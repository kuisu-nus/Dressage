export MODEL_ROOT=/eds-data/home/kuisu/01.data/03.model
export PROMPT_DATA="$PWD/data/restored_dressage_claw/dressage_claw_e2b.jsonl"
export DRESSAGE_SANDBOX_PROVIDER=e2b
export DRESSAGE_E2B_API_KEY=e2b_1e9c498b8c55fc869d4ed729dabb9aa4ad573f38
export DRESSAGE_E2B_BLACKBOX_PORT=31000
export DRESSAGE_PROXY_URL=https://buffoon-ladder-darkness.ngrok-free.dev
export MODEL_NAME=Qwen3-4B-Instruct-2507
export MODEL_CONFIG=qwen3-4B.sh
export TOKEN_BUILD_MODEL=qwen3_5
export RAY_TEMP_DIR="/tmp/ray"
export TMPDIR="/tmp/dressage"
export MODEL_ARGS_ROTARY_BASE=5000000

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