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

# Start the service (until reboot; service-enable makes it stick)
service-start:
    systemctl --user start kvllm

# Stop the service (until reboot; service-disable makes it stick)
service-stop:
    systemctl --user stop kvllm

# Restart the service (same model; use service-switch to change models)
service-restart:
    systemctl --user restart kvllm

# Switch the served model: write the key into deploy/kvllm.env and restart
service-switch key:
    uv run python -m kvllm.registry show {{key}} > /dev/null   # validate key first
    sed -i -E 's/^KVLLM_MODEL_KEY=.*/KVLLM_MODEL_KEY={{key}}/' deploy/kvllm.env
    systemctl --user restart kvllm
    @echo "switched to {{key}}; run 'just healthy' to wait for /v1"

# Show the service's systemd status
service-status:
    systemctl --user status kvllm --no-pager || true

# Follow the service's journal
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

# Restart the helper
helper-restart:
    systemctl --user restart kvllm-helper

# Show the helper's systemd status
helper-status:
    systemctl --user status kvllm-helper --no-pager || true

# Follow the helper's journal
helper-logs:
    journalctl --user -u kvllm-helper -f

# --- Eval (kvllm.evalrun + suites/; see model-research/evals/ and sprints/planning/) ---

# (Orchestrates kvllm.service around each model; writes scorecard + leaderboard + models.toml.)
# Evaluate registered model(s): serve → operational gate → Inspect suites → score
eval key *flags:
    uv run --group eval python -m kvllm.evalrun {{key}} {{flags}}

# Sweep the registry (resumable: skips models already scored on current suite versions)
eval-all *flags:
    uv run --group eval python -m kvllm.evalrun --all {{flags}}

# Prove the Docker sandbox path works (mock model, no GPU). Set DOCKER_HOST to test remote.
eval-sandbox-smoke:
    uv run --group eval python suites/sandbox_smoke.py

# (Runs in the sandbox; run before trusting a coding eval.)
# Self-test the coding suite: reference solutions must pass hidden tests (Docker; no GPU)
test-coding-suite:
    uv run --group eval python -m suites.coding_selftest

# Open the HTML leaderboard
eval-board:
    @echo "model-research/evals/leaderboard.html"

# --- Client lib (client/ = the kvllm-client distribution; see client/README.md) ---

# Unit tests for the client lib (own uv project; fakes only — no GPU, no network)
client-test:
    cd client && uv run --group dev pytest tests/ -q

# Lint + format-check
lint:
    uv run --group dev ruff check .
    uv run --group dev ruff format --check .

# Run the unit test suite (pure functions only — no network / no vLLM)
test:
    uv run --group dev --group eval --group test pytest tests/ -q

# Lint + unit tests (fast — no live model needed)
check: lint test client-test

# (Reference reports must score 1.0 mechanically; no GPU/model/judge needed.)
# Self-test the agentic suite: planted truths discoverable in the fixture (Docker)
test-agentic-suite:
    uv run --group eval python -m suites.agentic_selftest

# Self-test the vision suite: fixtures render/load + reference answers score 1.0 (no GPU/Docker)
test-vision-suite:
    uv run --group eval python -m suites.vision_selftest

# Browse eval transcripts (.eval logs) in the Inspect web viewer at http://localhost:7575
eval-view dir="eval-logs":
    uv run --group eval inspect view --log-dir {{dir}}
