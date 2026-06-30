# kvllm — vLLM serving harness on the kai RTX 5090.
# Recipes are the user-facing surface. Models live in models.toml (`just models-list`);
# vLLM holds one model per process, so switching models = stop one `serve`, start another.

set dotenv-load := true

# Default model key (a key from models.toml, not an HF repo). Override: KVLLM_MODEL_KEY=...
model_key := env("KVLLM_MODEL_KEY", "qwen2.5-7b-instruct")
port      := env("KVLLM_PORT", "8000")

# List recipes
default:
    @just --list

# List registered models (key, est VRAM, capabilities)
models-list:
    uv run python -m kvllm.registry list

# Show one model's config + the exact vllm serve command
models-show key:
    uv run python -m kvllm.registry show {{key}}

# Serve a registered model by key on an OpenAI-compatible /v1 endpoint
serve key=model_key:
    uv run python -m kvllm.registry serve {{key}}

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

# Show what the running server currently has loaded
loaded:
    curl -s "http://localhost:{{port}}/v1/models" | python -m json.tool

# Smoke-test tool calling via the raw OpenAI client (serve qwen2.5-7b-instruct first)
smoke-tools:
    KVLLM_MODEL=qwen2.5-7b-instruct uv run --group test python tests/smoke_tools.py

# Smoke-test LangChain reach (invoke + bind_tools)
smoke-langchain:
    KVLLM_MODEL=qwen2.5-7b-instruct uv run --group test python tests/smoke_langchain.py

# Smoke-test the DeepSeek-R1 distill (serve deepseek-r1-distill-qwen-7b first)
smoke-deepseek:
    KVLLM_MODEL=deepseek-r1-distill-qwen-7b uv run --group test python tests/smoke_deepseek.py

# Run the two exit-criteria smoke tests (qwen2.5-7b-instruct must be running)
smoke: smoke-tools smoke-langchain

# Lint + format-check
lint:
    uv run --group dev ruff check .
    uv run --group dev ruff format --check .
