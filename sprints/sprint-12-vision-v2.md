# Sprint 12 — Vision v2: classification, captioning, render-QA

_2026-07-04. Branch `12-vision-v2`. Follows sprint 11's v1, which hit its ceiling on
first contact (5 locals 94–100%, baselines 100%) — Ken's read: "mostly OCR"._

## Shipped (suite v2, 15 tasks)

- **Real-photo classification/captioning** (Ken's photos; downscaled, EXIF/GPS-stripped,
  originals never committed): p1 corgi breed + attire, p2 Raspberry Pi + network state,
  p3 caliper/ruler scan, p5 cyclist activity + rider count (Ken's own race photo, his OK).
  Skydive photo excluded — other people's faces, public repo.
- **p4 absence/honesty**: "how many people?" on the hardware photo → 0.
- **v9/v10 render-QA pair** (generated): broken flowchart (label spills through its box
  border) vs clean control — detect the defect without inventing one.
- max_tokens 2048→4096 (the reasoning-burn lesson, third appearance: the 27B emptied out
  mid-think on a photo).

## Calibration during rollout (the usual two rounds)

- v9 rubric gap: the 27B *found* the defect but called it "arrow overlaps the text" —
  overlap phrasing now accepted.
- **The bandana ruling** (Ken, in-task comment): it IS a bandana; "harness" stays
  unaccepted — the plausible misread earns 50% via partial credit, the precise read stays
  a differentiator. Evidence it works: Sonnet said "Shiba Inu... harness or bandana-style",
  Haiku invented "hair bows on its ears".

## Final column (amended v2, all nine models)

**gemma-4-31b 15/15 — the only perfect score, ahead of both baselines** (Sonnet 93%,
Haiku 93%; both miss the corgi task). Spread 87–100% with meaningful per-task signal:
p1 separates nearly everyone; v9 catches models that can't see rendering defects
(qwen3-vl says "renders correctly, no visual defects"). The 27B's 4096-token fix also
landed: no more empty answers, and its agentic (41% after the concurrency-cap reruns)
lifted it to `worth trying`.

## Notes

- Same-version amendments need `--force` — the stale-suite filter correctly refuses to
  re-run "current" suites, which is exactly right and exactly what it did.
- Cyclist/skydive privacy calls recorded above; the pattern (Ken supplies photos + ground
  truth, harness downscales/strips) is the template for future photo tasks.
