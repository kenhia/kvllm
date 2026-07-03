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

# --- Service (systemd user unit; see docs/03-deployment.md) ---

# Install/refresh the systemd user unit (renders deploy/kvllm.service.in)
service-install:
    bash deploy/install.sh

# Enable + start now, and at boot (linger is on)
service-enable:
    systemctl --user enable --now kvllm

# Stop + disable auto-start at boot (frees the GPU)
service-disable:
    systemctl --user disable --now kvllm

start:
    systemctl --user start kvllm
stop:
    systemctl --user stop kvllm
restart:
    systemctl --user restart kvllm

# Switch the served model: write the key into deploy/kvllm.env and restart
service-switch key:
    uv run python -m kvllm.registry show {{key}} > /dev/null   # validate key first
    sed -i -E 's/^KVLLM_MODEL_KEY=.*/KVLLM_MODEL_KEY={{key}}/' deploy/kvllm.env
    systemctl --user restart kvllm
    @echo "switched to {{key}}; run 'just healthy' to wait for /v1"

service-status:
    systemctl --user status kvllm --no-pager || true

service-logs:
    journalctl --user -u kvllm -f

# --- Helper web app (kvllm-helper.service; see docs/04-helper-app.md) ---

# Run the helper in the foreground (dev; reads deploy/kvllm.env for port/token)
helper-dev:
    uv run --group helper uvicorn kvllm.helper:app --host 0.0.0.0 --port "${KVLLM_HELPER_PORT:-8800}" --reload

# Enable + start the helper now and at boot
helper-enable:
    systemctl --user enable --now kvllm-helper

# Stop + disable the helper
helper-disable:
    systemctl --user disable --now kvllm-helper

helper-restart:
    systemctl --user restart kvllm-helper

helper-status:
    systemctl --user status kvllm-helper --no-pager || true

helper-logs:
    journalctl --user -u kvllm-helper -f

# --- Eval (kvllm.evalrun + evals/; see model-research/evals/ and sprints/fable-planning/) ---

# Evaluate registered model(s): serve → operational gate → Inspect suites → scorecard +
# leaderboard + models.toml. Orchestrates kvllm.service around each model.
eval key *flags:
    uv run --group eval python -m kvllm.evalrun {{key}} {{flags}}

# Sweep the registry (resumable: skips models already scored on current suite versions)
eval-all *flags:
    uv run --group eval python -m kvllm.evalrun --all {{flags}}

# Prove the Docker sandbox path works (mock model, no GPU). Set DOCKER_HOST to test remote.
eval-sandbox-smoke:
    uv run --group eval python evals/sandbox_smoke.py

# Self-test the coding suite: every task's reference solution must pass its hidden tests
# (needs Docker; no GPU/model). Run before trusting a coding eval.
test-coding-suite:
    uv run --group eval python -m evals.coding_selftest

# Open the HTML leaderboard
eval-board:
    @echo "model-research/evals/leaderboard.html"

# Lint + format-check
lint:
    uv run --group dev ruff check .
    uv run --group dev ruff format --check .

# Run the unit test suite (pure functions only — no network / no vLLM)
test:
    uv run --group dev --group eval --group test pytest tests/ -q

# Lint + unit tests (fast — no live model needed)
check: lint test

# Self-test the agentic suite: planted truths must be discoverable + reference reports
# must score 1.0 mechanically (needs Docker; no GPU/model/judge).
test-agentic-suite:
    uv run --group eval python -m evals.agentic_selftest
