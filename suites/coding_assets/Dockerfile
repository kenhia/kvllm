# Sandbox image for the S2 coding suite (sprints/fable-planning/06-coding-suite-spec.md).
# stdlib-only tasks + pytest for the hidden-test scorer. No network at runtime (compose sets
# network_mode: none) — everything the tasks need is baked in here.
FROM python:3.12-slim

# Pinned so a task's hidden-test run is reproducible across rebuilds.
RUN pip install --no-cache-dir "pytest==8.3.4"

# Non-root: model-generated code runs as this user; /workspace is its writable scratch.
RUN useradd --create-home --uid 1000 runner \
    && mkdir -p /workspace \
    && chown runner:runner /workspace
WORKDIR /workspace
USER runner

# Keep the container alive so Inspect can exec into it for the episode + scoring.
CMD ["sleep", "infinity"]
