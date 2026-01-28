#!/bin/bash
# vLLM Server Startup Script for HPC Batch Automation
# Starts vLLM with podman-hpc on 4 A100 GPUs

set -e

# Configuration
HOST="${VLLM_HOST:-127.0.0.1}"
PORT="${VLLM_PORT:-8008}"
MODEL="${VLLM_MODEL:-openai/gpt-oss-120b}"
TP_SIZE="${VLLM_TP_SIZE:-4}"
GPU_MEM_UTIL="${VLLM_GPU_MEM_UTIL:-0.60}"
VLLM_IMAGE="${VLLM_IMAGE:-docker.io/vllm/vllm-openai:v0.11.0}"

# Ensure HF_HOME is set
if [ -z "$HF_HOME" ]; then
    export HF_HOME="${HOME}/.cache/huggingface"
fi

echo "Starting vLLM server..."
echo "  Model: ${MODEL}"
echo "  Host: ${HOST}:${PORT}"
echo "  Tensor Parallel Size: ${TP_SIZE}"
echo "  GPU Memory Utilization: ${GPU_MEM_UTIL}"
echo "  HF_HOME: ${HF_HOME}"

# Start vLLM with podman-hpc
podman-hpc run --rm --gpu --net host --ipc=host \
    -e HF_HOME \
    -e HF_HUB_ENABLE_HF_TRANSFER=1 \
    -e VLLM_ATTENTION_BACKEND=TRITON_ATTN \
    -v "${HF_HOME}:${HF_HOME}" \
    "${VLLM_IMAGE}" \
    --model "${MODEL}" \
    --host "${HOST}" \
    --port "${PORT}" \
    --tensor-parallel-size "${TP_SIZE}" \
    --gpu-memory-utilization "${GPU_MEM_UTIL}" \
    --tool-call-parser openai \
    --enable-auto-tool-choice \
    --reasoning-parser openai_gptoss
