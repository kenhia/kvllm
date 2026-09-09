# Noise floor — `gemma-4-31b-it-awq` ×3 (2026-09-09)

| suite | n | min | max | band | median | mean |
| --- | --- | --- | --- | --- | --- | --- |
| `agentic` | 3 | 0.330 | 0.500 | **0.170** | 0.330 | 0.387 |
| `code` | 3 | 0.930 | 1.000 | **0.070** | 0.990 | 0.973 |
| `judged` | 3 | 0.680 | 0.850 | **0.170** | 0.750 | 0.760 |
| `tools` | 3 | 1.000 | 1.000 | **0.000** *(identical)* | 1.000 | 1.000 |
| `vision` | 3 | 0.970 | 1.000 | **0.030** | 0.970 | 0.980 |

Per-run pass rates:

- `agentic`: 0.330, 0.500, 0.330
- `code`: 1.000, 0.990, 0.930
- `judged`: 0.750, 0.850, 0.680
- `tools`: 1.000, 1.000, 1.000
- `vision`: 1.000, 0.970, 0.970

**Published to the board:** run 1. Every eval invocation rewrites the scorecard and the leaderboard, so without a choice here the board would show whichever run finished last, presented as *the* number.

**Read the band as a floor, not the uncertainty.** All N runs happened in one night, which holds provider-side drift roughly constant, so this is a *within-night* figure and a lower bound on real run-to-run variance across days. The honest board language is "differences below X are definitely not meaningful", not "X is the total uncertainty". A local model has no provider-drift confound, so its band is the cleaner read on pure harness noise — report the two separately rather than pooling them.

N=3 bounds a band. It does not give a trustworthy standard deviation and is not publishable as a variance study (korg:1499).
