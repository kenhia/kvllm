# Fixture-homelab image for the S3 agentic suite (fable-planning/07). The model investigates
# this box with bash; systemctl/journalctl/korg are shims rendering planted scenario state
# (a slim container can't run real systemd). Scenario selected by /workspace/.scenario,
# written per-sample via Sample(files=...).
FROM python:3.12-slim

# ps/top for the a7 stray-process task; nothing else — the box should feel bare-but-real.
RUN apt-get update && apt-get install -y --no-install-recommends procps \
    && rm -rf /var/lib/apt/lists/*

COPY scenarios.json /usr/share/hostinfo/scenarios.json
COPY shims/systemctl shims/journalctl shims/korg /usr/local/bin/
RUN chmod 0755 /usr/local/bin/systemctl /usr/local/bin/journalctl /usr/local/bin/korg \
    && echo "fixhost-01 — Ken's homelab (fixture)" > /etc/motd \
    # the REAL cert-renewal script (every scenario) — a4's cron file references the .hs typo
    && printf '#!/bin/sh\n# renew TLS certs via internal CA\nexit 0\n' \
       > /usr/local/bin/renew-cert.sh \
    && chmod 0755 /usr/local/bin/renew-cert.sh

# Non-root runner; scenario-touched paths are runner-writable so per-sample `setup` scripts
# can materialize state (cron typo file, runaway log) without root. Deviation from the spec's
# root-owned /fixture noted in the sprint doc: shims run as runner and must read the state
# anyway; the ground truth is the same data the shims render, so readability is not a cheat.
RUN useradd --create-home --uid 1000 runner \
    && mkdir -p /workspace /var/log/kvllm /etc/cron.d /var/lib/backup \
    && chown runner:runner /workspace /var/log/kvllm /etc/cron.d /var/lib/backup
WORKDIR /workspace
USER runner

CMD ["sleep", "infinity"]
