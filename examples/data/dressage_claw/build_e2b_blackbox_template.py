"""Build an E2B dressage_claw blackbox template with an isolated BBS runtime.

The template replicates the dressage_claw sandbox runtime: python3, curl, patch,
openclaw, BlackboxServer (started on port 31000), and the Python packages the
mock services need (fastapi/uvicorn/pydantic/httpx/openai).

Usage::

    # Self-hosted E2B (sets E2B_API_URL / E2B_SANDBOX_URL, stages only
    # blackbox_server as the build context, and relays the build upload port).
    ./examples/data/dressage_claw/build_e2b_blackbox_template.sh

    # E2B Cloud, or a self-hosted stack you already exported the endpoints for.
    # Run this from a directory that contains only blackbox_server: the whole
    # file context (".", minus .dockerignore) is uploaded to the builder.
    E2B_API_KEY=e2b_... \
    E2B_API_URL=http://192.168.36.108:3000 \
    E2B_SANDBOX_URL=http://192.168.36.108:3002 \
    BUILD_FROM_PUBLIC_IMAGE=1 \
    TASK_IMAGE='node:24.22.1-bookworm-slim' \
    TEMPLATE_NAME='e2b-dressage-claw-blackbox' \
    python examples/data/dressage_claw/build_e2b_blackbox_template.py

Only ``blackbox_server`` (the HTTP adapter) is installed into the isolated
venv — the full ``dressage`` package is not needed inside the sandbox since
it runs on the training machine.

Environment variables baked into the template:
    BBS_HOST=0.0.0.0          BlackboxServer bind address
    BBS_PORT=31000            BlackboxServer listen port
    BBS_RUNTIME_ROOT=/workspace_sandbox/blackbox_server_runtime
                              Runtime directory root

Optional build-time variables:
    BBS_PYTHON_VERSION        Python version for the BBS venv (default: 3.11)
    E2B_TEMPLATE_CPU_COUNT    Template CPU cores (default: 2)
    E2B_TEMPLATE_MEMORY_MB    Template memory in MB (default: 1024)
    E2B_MIN_FREE_DISK_MB      Free build disk requested from the API (default: 4096)
    OPENCLAW_VERSION          openclaw version for public-image mode
    OPENCLAW_NODE_VERSION     Node.js runtime for openclaw (default: 24.22.1)
"""

from __future__ import annotations

import os
from pathlib import Path

from e2b import Template, default_build_logger, wait_for_port

try:
    # E2B renamed this exception in different Python SDK releases.  Keep the
    # builder usable with both the older SDK used by the Dressage images and
    # the current SDK.
    from e2b import TemplateBuildError as _E2BBuildError
except ImportError:  # pragma: no cover - depends on the installed E2B SDK
    from e2b import BuildException as _E2BBuildError


DEFAULT_BBS_PYTHON_VERSION = "3.11"


def _env(name: str, *, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if not value:
        raise SystemExit(f"{name} is required")
    return value


def _patch_build_request_min_free_disk(min_free_mb: int) -> None:
    """Request free build disk via the API's ``minFreeDiskMb`` field.

    The pinned SDK (2.24) predates ``min_free_disk_mb``; newer SDKs add the
    field to the v3 template-build request.  Inject it by wrapping
    ``request_build`` so self-hosted builders have room for npm/uv installs.
    Older API servers that do not know the field fall back to the original
    request.
    """
    if min_free_mb <= 0:
        return
    try:
        import e2b.template_sync.main as template_sync_main
        from e2b.template_sync import build_api
    except ImportError:  # pragma: no cover - depends on the installed SDK
        print("warning: e2b template_sync unavailable; not requesting extra disk")
        return

    original_request_build = template_sync_main.request_build

    def request_build_with_min_free_disk(
        client: object, name: str, tags: object, cpu_count: int, memory_mb: int
    ) -> object:
        body = build_api.TemplateBuildRequestV3(
            name=name,
            tags=tags if tags else build_api.UNSET,
            cpu_count=cpu_count,
            memory_mb=memory_mb,
        )
        body.additional_properties["minFreeDiskMb"] = min_free_mb
        response = build_api.post_v3_templates.sync_detailed(client=client, body=body)
        if response.status_code >= 300:
            message = str(getattr(response.parsed, "message", "") or "")
            if "minFreeDiskMb" in message:
                print(
                    "warning: this E2B API does not accept minFreeDiskMb; "
                    "retrying without extra build disk"
                )
                return original_request_build(
                    client=client,
                    name=name,
                    tags=tags,
                    cpu_count=cpu_count,
                    memory_mb=memory_mb,
                )
            raise build_api.handle_api_exception(response, build_api.BuildException)
        if response.parsed is None:
            raise build_api.BuildException("Failed to request build")
        return response.parsed

    template_sync_main.request_build = request_build_with_min_free_disk


def build_template() -> object:
    task_image = _env("TASK_IMAGE")
    template_name = _env("TEMPLATE_NAME")
    python_version = _env("BBS_PYTHON_VERSION", default=DEFAULT_BBS_PYTHON_VERSION)
    from_public = os.environ.get("BUILD_FROM_PUBLIC_IMAGE") == "1"
    openclaw_version = _env("OPENCLAW_VERSION", default="2026.6.6")
    node_version = _env("OPENCLAW_NODE_VERSION", default="24.22.1")
    min_free_disk_mb = int(os.environ.get("E2B_MIN_FREE_DISK_MB", "4096"))
    _patch_build_request_min_free_disk(min_free_disk_mb)

    if not Path("blackbox_server").is_dir():
        raise SystemExit(
            "run this script from the Dressage repository root "
            "(expected ./blackbox_server)"
        )

    template = (
        Template(file_context_path=".")
        .from_image(task_image)
        .set_user("root")
        .set_envs(
            {
                # Match the local bwrap runner's blackbox environment.  The
                # E2B sandbox has no supervisor slot, but these names are
                # intentionally kept stable for task/setup scripts.
                "HOME": "/home/blackbox",
                "XDG_CONFIG_HOME": "/home/blackbox/.config",
                "XDG_CACHE_HOME": "/home/blackbox/.cache",
                "TMPDIR": "/tmp",
                # The official python:slim image has a second Debian
                # /usr/bin/python3 without pip. Keep /usr/local first for
                # task-side `python3` after uv installs its dependencies.
                # The openclaw installer drops its user-space node runtime
                # under $HOME/.openclaw when the image has no system node,
                # so keep those bins on PATH as well.
                "PATH": (
                    "/home/blackbox/.openclaw/tools/node/bin:"
                    "/home/blackbox/.openclaw/bin:"
                    "/home/blackbox/.npm-global/bin:"
                    "/home/blackbox/.local/bin:"
                    "/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin"
                ),
                "OPENCLAW_BIN": "/usr/local/bin/openclaw",
                "OPENCLAW_NODE_VERSION": node_version,
                "BBS_HOST": "0.0.0.0",
                "BBS_PORT": "31000",
                "BBS_RUNTIME_ROOT": "/workspace_sandbox/blackbox_server_runtime",
                "DRESSAGE_BLACKBOX_RUNTIME_ROOT": "/workspace_sandbox/blackbox_server_runtime",
                "DRESSAGE_BLACKBOX_SLOT_ID": "e2b",
                "DRESSAGE_BLACKBOX_SLOT_DIR": "/workspace_sandbox",
                "DRESSAGE_BLACKBOX_SLOT_GENERATION": "0",
                "DRESSAGE_BLACKBOX_SLOT_PORT": "31000",
                "DRESSAGE_BLACKBOX_SUPERVISOR_RUN_ID": "e2b-template",
                "CUDA_VISIBLE_DEVICES": "",
                "NVIDIA_VISIBLE_DEVICES": "void",
                # OMNI model for judge evaluation (optional, but useful for testing).  The
                "OMNI_CLAW_EVAL_ENABLE_JUDGE": "1",
                "OMNI_CLAW_EVAL_JUDGE_MODEL": "deepseek-flash",
                "OMNI_CLAW_EVAL_JUDGE_BASE_URL": "https://api.deepseek.com",
                "OMNI_CLAW_EVAL_JUDGE_API_KEY":"sk-d3243bb4cc974e3daa39a6fbbea87747"
            }
        )
    )
    if from_public:
        # Install openclaw inside the template build (normally baked into
        # the base image by docker/build.sh).  The default base image is
        # node:*-bookworm-slim so Node does not have to be written into the
        # builder's small working space; python3 comes from apt.  Other base
        # images fall back to the official Node tarball (with no supported
        # system Node, the openclaw installer apt-installs build-essential,
        # which overflows the self-hosted builder's disk).
        template = template.run_cmd(
            "install -d -m 0777 /home/blackbox /workspace_sandbox /data && "
            "touch /home/blackbox/.bashrc && "
            "apt-get update && "
            "apt-get install -y --no-install-recommends "
            "bash ca-certificates curl git patch xz-utils python3 && "
            "rm -rf /var/lib/apt/lists/* && "
            "node_ok=0; "
            'if command -v node >/dev/null 2>&1; then '
            '  node_ver="$(node --version 2>/dev/null | tr -d "v")"; '
            '  node_major="${node_ver%%.*}"; node_rest="${node_ver#*.}"; '
            '  node_minor="${node_rest%%.*}"; '
            '  if [ "${node_major:-0}" -gt 26 ] 2>/dev/null || '
            '     { [ "${node_major:-0}" -eq 26 ] && '
            '       [ "${node_minor:-0}" -ge 12 ]; } 2>/dev/null || '
            '     { [ "${node_major:-0}" -eq 24 ] && '
            '       [ "${node_minor:-0}" -ge 22 ]; } 2>/dev/null; '
            "  then node_ok=1; fi; "
            "fi; "
            'if [ "$node_ok" != "1" ]; then '
            '  node_arch="$(uname -m)"; '
            '  case "$node_arch" in x86_64) node_arch=x64 ;; '
            "  aarch64|arm64) node_arch=arm64 ;; "
            '  *) echo "unsupported architecture: $node_arch"; exit 1 ;; esac; '
            f'  node_version="{node_version}"; '
            '  curl -fsSL "https://nodejs.org/dist/v${node_version}/'
            'node-v${node_version}-linux-${node_arch}.tar.xz" '
            "  -o /tmp/node.tar.xz && "
            "  tar -xJf /tmp/node.tar.xz -C /usr/local --strip-components=1 && "
            "  rm -f /tmp/node.tar.xz && "
            "  ln -sf /usr/local/bin/node /usr/bin/node && "
            "  ln -sf /usr/local/bin/npm /usr/bin/npm && "
            "  ln -sf /usr/local/bin/npx /usr/bin/npx; "
            "fi; "
            "node --version && npm --version && "
            # Keep npm's cache and temp files in RAM so the install fits on
            # the small builder disk.
            "export NPM_CONFIG_CACHE=/dev/shm/npm-cache TMPDIR=/dev/shm && "
            "curl -fsSL --connect-timeout 15 --max-time 180 "
            "https://openclaw.ai/install.sh | "
            f"bash -s -- --version {openclaw_version} --no-onboard && "
            "npm cache clean --force >/dev/null 2>&1 || true; "
            "rm -rf /dev/shm/npm-cache /var/cache/apt/archives/* 2>/dev/null || true"
        )
    if not from_public:
        # Public-image mode already installed these in the openclaw step;
        # a second apt-get run there hangs on this self-hosted builder.
        template = template.run_cmd(
            "apt-get update && "
            "apt-get install -y --no-install-recommends bash ca-certificates curl patch && "
            "rm -rf /var/lib/apt/lists/*"
        )
    template = (
        template
        # Create an isolated venv for BlackboxServer so the task image's
        # Python environment stays untouched. Use uv for both the isolated BBS
        # environment and task dependencies: slim images commonly omit pip.
        .run_cmd(
            "install -d -m 0777 /home/blackbox /workspace_sandbox /data "
            "/workspace_sandbox/blackbox_server_runtime && "
            "curl -LsSf --connect-timeout 15 --max-time 180 "
            "https://astral.sh/uv/install.sh | sh && "
            # Reuse the image's python3 instead of downloading a managed
            # interpreter; the self-hosted builder disk is only ~1 GB.
            f"/home/blackbox/.local/bin/uv venv --python {python_version} "
            "--python-preference only-system /opt/dressage-bbs-venv && "
            "UV_HTTP_TIMEOUT=60 UV_HTTP_RETRIES=3 "
            "/home/blackbox/.local/bin/uv pip install "
            "--python /opt/dressage-bbs-venv/bin/python setuptools wheel && "
            "UV_HTTP_TIMEOUT=60 UV_HTTP_RETRIES=3 "
            "/home/blackbox/.local/bin/uv pip install --system --break-system-packages "
            '--python "$(command -v python3)" '
            "fastapi uvicorn pydantic httpx openai"
        )
        .copy(".", "/root/Dressage")
        .run_cmd(
            "/home/blackbox/.local/bin/uv pip install "
            "--python /opt/dressage-bbs-venv/bin/python "
            "--no-cache-dir --no-build-isolation "
            "/root/Dressage/blackbox_server"
        )
        # Keep the image small enough for the self-hosted builder disk.
        .run_cmd(
            "rm -rf /root/.npm /home/blackbox/.npm "
            "/root/.cache/uv /home/blackbox/.cache/uv || true"
        )
        # Resolve openclaw wherever the installer/image put it.  With a public
        # slim image the installer provisions a user-space node runtime under
        # $HOME/.openclaw; prebuilt task images may ship /usr/bin/openclaw.
        # Link it to the stable OPENCLAW_BIN path the runtime expects.
        .run_cmd(
            'openclaw_bin="$(command -v openclaw || true)"; '
            'if [ -z "$openclaw_bin" ]; then '
            '  for candidate in '
            '    /usr/local/bin/openclaw /usr/bin/openclaw '
            '    /home/blackbox/.local/bin/openclaw '
            '    /home/blackbox/.npm-global/bin/openclaw '
            '    /home/blackbox/.openclaw/bin/openclaw '
            '    /home/blackbox/.openclaw/tools/node/bin/openclaw '
            '    /root/.local/bin/openclaw /root/.npm-global/bin/openclaw '
            '    /root/.openclaw/bin/openclaw '
            '    /root/.openclaw/tools/node/bin/openclaw; do '
            '    if [ -x "$candidate" ]; then openclaw_bin="$candidate"; break; fi; '
            '  done; '
            'fi; '
            'if [ -z "$openclaw_bin" ]; then '
            '  echo "ERROR: openclaw executable not found"; exit 1; '
            'fi; '
            # Never link a path to itself: command -v already returns
            # /usr/local/bin/openclaw for npm installs, and ln -sf with
            # identical src/dest creates a self-referencing loop.
            'if [ "$openclaw_bin" != "/usr/local/bin/openclaw" ]; then '
            '  ln -sf "$openclaw_bin" /usr/local/bin/openclaw; '
            'fi; '
            'if [ "$openclaw_bin" != "/usr/bin/openclaw" ]; then '
            '  ln -sf "$openclaw_bin" /usr/bin/openclaw; '
            'fi; '
            '/usr/local/bin/openclaw --version'
        )
        .set_start_cmd(
            "install -d -m 0777 /home/blackbox /workspace_sandbox /data "
            "/workspace_sandbox/blackbox_server_runtime && "
            "cd /workspace_sandbox && "
            "BBS_HOST=0.0.0.0 BBS_PORT=31000 "
            "BBS_RUNTIME_ROOT=/workspace_sandbox/blackbox_server_runtime "
            "DRESSAGE_BLACKBOX_RUNTIME_ROOT=/workspace_sandbox/blackbox_server_runtime "
            "DRESSAGE_BLACKBOX_SLOT_ID=e2b DRESSAGE_BLACKBOX_SLOT_DIR=/workspace_sandbox "
            "DRESSAGE_BLACKBOX_SLOT_GENERATION=0 DRESSAGE_BLACKBOX_SLOT_PORT=31000 "
            "DRESSAGE_BLACKBOX_SUPERVISOR_RUN_ID=e2b-template "
            "HOME=/home/blackbox XDG_CONFIG_HOME=/home/blackbox/.config "
            "XDG_CACHE_HOME=/home/blackbox/.cache TMPDIR=/tmp "
            "OPENCLAW_BIN=/usr/local/bin/openclaw "
            "/opt/dressage-bbs-venv/bin/python -m blackbox_server.main",
            wait_for_port(31000),
        )
    )

    try:
        return Template.build(
            template,
            template_name,
            cpu_count=int(os.environ.get("E2B_TEMPLATE_CPU_COUNT", "2")),
            # 4 GB makes the self-hosted builder fail with an opaque internal
            # error; 1 GB starts it and is enough for openclaw + BlackboxServer.
            memory_mb=int(os.environ.get("E2B_TEMPLATE_MEMORY_MB", "1024")),
            skip_cache=os.environ.get("E2B_SKIP_CACHE") == "1",
            on_build_logs=default_build_logger(),
        )
    except _E2BBuildError as exc:
        raise SystemExit(f"failed to build {template_name}: {exc}") from exc


if __name__ == "__main__":
    info = build_template()
    print({"docker_image": os.environ["TASK_IMAGE"], "template": info.name})
