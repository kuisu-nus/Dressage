export MODEL_ROOT=/eds-data/home/kuisu/01.data/03.model
export PROMPT_DATA="$PWD/data/restored_dressage_claw/dressage_claw_e2b.jsonl"
export DRESSAGE_SANDBOX_PROVIDER=e2b

# --- self-hosted E2B (deployed at 192.168.36.108) ---------------------------
# The e2b SDK reads E2B_API_URL / E2B_SANDBOX_URL; Dressage's provider reads
# DRESSAGE_E2B_API_KEY.  Keep the key in one variable so both stay in sync.
export E2B_HOST=192.168.36.108
export E2B_API_URL="http://${E2B_HOST}:3000"
export E2B_SANDBOX_URL="http://${E2B_HOST}:3002"
export E2B_DASHBOARD_URL="http://${E2B_HOST}:3001"
export E2B_API_KEY=e2b_3dbbeb280b46138d64d9f6a608ecf31e87848ca9
export DRESSAGE_E2B_API_KEY="${E2B_API_KEY}"
export DRESSAGE_E2B_BLACKBOX_PORT=31000
# Ray workers are forked processes; make sure they can see the SDK endpoints.
export DRESSAGE_EXTRA_RUNTIME_ENV_KEYS="E2B_API_URL,E2B_SANDBOX_URL,E2B_DASHBOARD_URL,E2B_API_KEY,E2B_DOMAIN"

# --- proxy reachability ------------------------------------------------------
# The Dressage proxy is started by the inner script on this node (RANK 0) and
# listens on PROXY_PORT.  Two different URLs are needed:
#
#   DRESSAGE_PROXY_URL         used by this node (health check, pause/resume,
#                              finalize/read_trajectory) -> the LAN IP.
#   DRESSAGE_PROXY_PUBLIC_URL  handed to the agent inside the sandbox.
#
# E2B sandboxes on 192.168.36.108 cannot route to RFC1918 addresses, so they
# reach this node through a TEST-NET address DNAT'd on the E2B host.  Run once
# on 192.168.36.108 (re-run after every reboot of that host):
#
#   iptables -t nat -A OUTPUT -d 203.0.113.10 -p tcp --dport 8800 \
#       -j DNAT --to-destination 10.230.1.2:8800
#
# Then the sandbox reaches the proxy as 203.0.113.10:8800.
export PROXY_PORT=8800
LOCAL_PROXY_HOST="${LOCAL_PROXY_HOST:-$(hostname -I | awk '{print $1}')}"
export DRESSAGE_PROXY_URL="${DRESSAGE_PROXY_URL:-http://${LOCAL_PROXY_HOST}:${PROXY_PORT}}"
export PROXY_PUBLIC_ADDR="${PROXY_PUBLIC_ADDR:-203.0.113.10}"
export DRESSAGE_PROXY_PUBLIC_URL="${DRESSAGE_PROXY_PUBLIC_URL:-http://${PROXY_PUBLIC_ADDR}:${PROXY_PORT}}"
export MODEL_NAME=Qwen3-4B-Instruct-2507
export MODEL_CONFIG=qwen3-4B.sh
export TOKEN_BUILD_MODEL=qwen3_5
export RAY_TEMP_DIR="/tmp/ray"
export TMPDIR="/tmp/dressage"
export MODEL_ARGS_ROTARY_BASE=5000000

# Ray's default GCS port (6379) is already taken on this node by a Redis
# instance we don't own, so pin the head node to a free port.  Workers join
# through the same RAY_PORT, so it only needs to be free on every node.
# Must be OUTSIDE Ray's default worker port range 10002-19999 (a port inside
# it makes ray start abort with "trying to use a port number ... that is used
# by other components").
export RAY_PORT="${RAY_PORT:-26379}"
if [[ "${RAY_PORT}" -ge 10002 && "${RAY_PORT}" -le 19999 ]]; then
  echo "RAY_PORT=${RAY_PORT} is inside Ray's worker port range (10002-19999); pick another" >&2
  exit 1
fi
if netstat -tln 2>/dev/null | awk '{print $4}' | grep -qE "[:.]${RAY_PORT}\$"; then
  echo "RAY_PORT=${RAY_PORT} is already in use on this node; pick another" >&2
  exit 1
fi

export WANDB_API_KEY="8dcf2fbd5ebb9660ff18edac681e71aaefd11228"
export WANDB_MODE="online"
export WANDB_KEY="8dcf2fbd5ebb9660ff18edac681e71aaefd11228"

export GLOO_SOCKET_IFNAME=bond0
export TP_SOCKET_IFNAME=bond0
export NCCL_SOCKET_IFNAME=bond0

export RAY_DEBUG_POST_MORTEM=1     # 失败后进入 post-mortem pdb
export RAY_PDB=0
export USE_WANDB=1
export DEBUG_ROLLOUT_ONLY=0
export SGLANG_SERVER_CONCURRENCY=2


export WORLD_SIZE=1
export NNODES=1
export CP_SIZE=4
# export GLOBAL_BATCH_SIZE=8
# export ROLLOUT_MAX_RESPONSE_LEN=8191
# export COMPACT_RESERVE_TOKENS=4096   # 或更小，确保 CONTEXT_WINDOW - COMPACT_RESERVE_TOKENS > 0

bash examples/scripts/run_dressage_claw_qwen3.6_35b_a3b_sync_4_node.sk.sh