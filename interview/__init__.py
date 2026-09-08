"""The RA interview — envelope probes and adaptive interview tooling (sprint 19).

Talks to a served /v1 endpoint; never orchestrates kvllm.service. `interview.serve` starts
a registry model with overrides for the envelope study; the probe modules drive whatever
is served. Outputs land under model-research/ra-interview/.
"""
