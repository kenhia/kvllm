# kvllm — vLLM serving harness on the kai RTX 5090.
# Recipes are the user-facing surface. Sprint 2 will grow this into a model registry;
# for now it serves one model per process (vLLM holds one model per process).

set dotenv-load := true

# Defaults (override on the CLI, e.g. `just serve model=Qwen/Qwen2.5-7B-Instruct`)
model      := env("KVLLM_MODEL", "Qwen/Qwen2.5-7B-Instruct")
parser     := env("KVLLM_TOOL_PARSER", "hermes")
port       := env("KVLLM_PORT", "8000")
max_len    := env("KVLLM_MAX_MODEL_LEN", "8192")
gpu_util   := env("KVLLM_GPU_UTIL", "0.9")

# List recipes
default:
    @just --list

# Serve a tool-capable model on an OpenAI-compatible /v1 endpoint
serve:
    uv run vllm serve {{model}} \
        --enable-auto-tool-choice --tool-call-parser {{parser}} \
        --gpu-memory-utilization {{gpu_util}} \
        --max-model-len {{max_len}} \
        --port {{port}}

# Serve the DeepSeek-R1 distill (reasoning model; separates <think> via the R1 parser)
serve-deepseek:
    uv run vllm serve deepseek-ai/DeepSeek-R1-Distill-Qwen-7B \
        --enable-auto-tool-choice --tool-call-parser hermes \
        --reasoning-parser deepseek_r1 \
        --gpu-memory-utilization {{gpu_util}} \
        --max-model-len {{max_len}} \
        --port {{port}}

# Wait until the server answers /v1/models (up to 10 min for a cold model download)
healthy:
    #!/usr/bin/env bash
    for i in $(seq 1 600); do
      if curl -sf "http://localhost:{{port}}/v1/models" > /dev/null 2>&1; then
        echo "vLLM ready (${i}s)"; exit 0
      fi
      sleep 1
    done
    echo "ERROR: vLLM not ready after 600s"; exit 1

# List models the server currently has loaded
models:
    curl -s "http://localhost:{{port}}/v1/models" | python -m json.tool

# Smoke-test tool calling via the raw OpenAI client
smoke-tools:
    uv run --group test python tests/smoke_tools.py

# Smoke-test LangChain reach (invoke + bind_tools)
smoke-langchain:
    uv run --group test python tests/smoke_langchain.py

# Smoke-test the DeepSeek-R1 distill (serve-deepseek must be running)
smoke-deepseek:
    KVLLM_MODEL=deepseek-ai/DeepSeek-R1-Distill-Qwen-7B \
        uv run --group test python tests/smoke_deepseek.py

# Run the two exit-criteria smoke tests (Qwen must be running)
smoke: smoke-tools smoke-langchain

# Lint + format-check
lint:
    uv run --group dev ruff check .
    uv run --group dev ruff format --check .
