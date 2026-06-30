#!/usr/bin/env bash
# Render and install the kvllm systemd *user* services (model server + helper web app).
# Idempotent: re-run after editing a template or moving the repo. No sudo.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UNIT_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
ENV_FILE="$REPO/deploy/kvllm.env"

UV="$(command -v uv || true)"
if [[ -z "$UV" ]]; then
  echo "error: 'uv' not found on PATH" >&2
  exit 1
fi

# Seed the env file from the example on first install (never clobber an existing one).
if [[ ! -f "$ENV_FILE" ]]; then
  cp "$REPO/deploy/kvllm.env.example" "$ENV_FILE"
  echo "created $ENV_FILE (from example)"
fi

# Backfill the helper port if an older env file predates it (don't touch the token).
if ! grep -q '^KVLLM_HELPER_PORT=' "$ENV_FILE"; then
  printf '\n# helper web app\nKVLLM_HELPER_PORT=8800\n' >> "$ENV_FILE"
  echo "added KVLLM_HELPER_PORT=8800 to $ENV_FILE"
fi

mkdir -p "$UNIT_DIR"
render() {  # <template> <dest>
  sed -e "s|@WORKDIR@|$REPO|g" -e "s|@UV@|$UV|g" "$1" > "$2"
  echo "installed $2"
}
render "$REPO/deploy/kvllm.service.in"        "$UNIT_DIR/kvllm.service"
render "$REPO/deploy/kvllm-helper.service.in" "$UNIT_DIR/kvllm-helper.service"

systemctl --user daemon-reload
echo "daemon-reloaded."

if ! grep -qE '^KVLLM_HELPER_TOKEN=.+' "$ENV_FILE"; then
  echo
  echo "NOTE: KVLLM_HELPER_TOKEN is not set in $ENV_FILE — the helper's control actions"
  echo "      (switch/restart/stop) will be disabled until you set one:"
  echo "        echo \"KVLLM_HELPER_TOKEN=\$(openssl rand -hex 16)\" >> deploy/kvllm.env"
fi

echo
echo "Next:"
echo "  just service-enable      # model server: start now + at boot"
echo "  just helper-enable       # web panel:    start now + at boot"
echo "  just helper-status"
