#!/usr/bin/env bash
# Render and install the kvllm systemd *user* service.
# Idempotent: re-run after editing the template or moving the repo. No sudo.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UNIT_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
UNIT="$UNIT_DIR/kvllm.service"
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

mkdir -p "$UNIT_DIR"
sed -e "s|@WORKDIR@|$REPO|g" -e "s|@UV@|$UV|g" "$REPO/deploy/kvllm.service.in" > "$UNIT"
echo "installed $UNIT"

systemctl --user daemon-reload
echo "daemon-reloaded."
echo
echo "Next:"
echo "  just service-enable      # start now + auto-start at boot (linger is on)"
echo "  just service-status"
echo "  just service-logs"
