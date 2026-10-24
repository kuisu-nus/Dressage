export MODEL_ROOT=/eds-data/home/kuisu/01.data/03.model
export PROMPT_DATA="$PWD/data/swegym-train-claude-code-e2b.jsonl"
export DRESSAGE_SANDBOX_PROVIDER=e2b
export DRESSAGE_E2B_API_KEY=e2b_1e9c498b8c55fc869d4ed729dabb9aa4ad573f38
export DRESSAGE_E2B_BLACKBOX_PORT=31000
export DRESSAGE_PROXY_URL=https://bottling-knelt-predator.ngrok-free.dev
export MODEL_NAME=Qwen3-4B-Instruct-2507
export MODEL_CONFIG=qwen3-4B.sh
export RAY_TEMP_DIR="/tmp/ray"
export TMPDIR="/tmp/dressage"
export MODEL_ARGS_ROTARY_BASE=5000000

export GLOO_SOCKET_IFNAME=bond0
export TP_SOCKET_IFNAME=bond0
export NCCL_SOCKET_IFNAME=bond0

export RAY_DEBUG_POST_MORTEM=1     # 失败后进入 post-mortem pdb
export RAY_PDB=1
export USE_WANDB=1
export DEBUG_ROLLOUT_ONLY=0
export SGLANG_SERVER_CONCURRENCY=2

bash examples/scripts/run_dressage_swegym_qwen3.5_4b_claude_code_sync_4_node.sh