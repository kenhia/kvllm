"""Inspect AI task definitions for the kvllm eval harness (see sprints/fable-planning/).

One module per suite; each exports a @task and a VERSION int that is stamped into scorecards
so the leaderboard can mark stale scores when a suite changes.
"""
