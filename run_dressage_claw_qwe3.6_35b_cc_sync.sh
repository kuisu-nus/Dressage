export MODEL_ROOT=/eds-data/home/kuisu/01.data/03.model
export PROMPT_DATA="$PWD/data/restored_dressage_claw/dressage_claw_e2b.jsonl"
export DRESSAGE_SANDBOX_PROVIDER=e2b
export DRESSAGE_E2B_API_KEY=e2b_1e9c498b8c55fc869d4ed729dabb9aa4ad573f38
export DRESSAGE_E2B_BLACKBOX_PORT=31000
export DRESSAGE_PROXY_URL=https://buffoon-ladder-darkness.ngrok-free.dev
export MODEL_NAME=Qwen3.6-35B-A3B
export MODEL_CONFIG=qwen3.5-35B-A3B.sh
export RAY_TEMP_DIR="/tmp/ray"
export TMPDIR="/tmp/dressage"
# export MODEL_ARGS_ROTARY_BASE=5000000

export GLOO_SOCKET_IFNAME=bond0
export TP_SOCKET_IFNAME=bond0
export NCCL_SOCKET_IFNAME=bond0

# export RAY_DEBUG_POST_MORTEM=1     # 失败后进入 post-mortem pdb
# export RAY_PDB=1
# export USE_WANDB=1
export DEBUG_ROLLOUT_ONLY=0
export SGLANG_SERVER_CONCURRENCY=2

export WORLD_SIZE=1
export RANK=0
export ROLLOUT_BATCH_SIZE=2
export GLOBAL_BATCH_SIZE=16
export MAX_TOKENS_PER_GPU=4096
export CP_SIZE=4
export COMPACT_RESERVE_TOKENS=1024
bash examples/scripts/run_dressage_claw_qwen3.6_35b_a3b_sync_4_node.sh