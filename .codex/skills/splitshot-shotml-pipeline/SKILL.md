---
name: splitshot-shotml-pipeline
description: Validate SplitShot ShotML, detection, timing, corpus, training, and analysis pipeline changes with deterministic repo scripts and artifacts.
---
Use this skill when changes touch:
- src/splitshot/analysis/
- ShotML settings
- beep detection
- shot detection
- timing analysis
- proposal generation
- training corpus tooling
- media analysis workflows
- anything affecting detection quality or timing accuracy

Core rule:
Detection and timing changes must be validated with deterministic analysis tests or artifacts, not just code inspection.

Inspect:
- src/splitshot/analysis/
- scripts/analysis/
- tests/analysis/
- .training usage, if present
- changed settings, thresholds, proposal logic, or timing assumptions

Quick verification:
Run analysis tests:

```bash
uv run pytest tests/analysis/
```

Preflight a video when a sample path is available:

```bash
uv run python scripts/analysis/analyze_video_shots.py /path/to/video.mp4 --format table --json-output artifacts/shot-preview.json
```

Corpus workflow when training data is involved:

```bash
uv run python scripts/analysis/audit_training_corpus.py .training --format table --json-output artifacts/training-corpus-audit.json
```

Refresh or bootstrap manifest when labels/corpus changed:

```bash
uv run python scripts/analysis/bootstrap_training_manifest.py .training --output .training/shotml-label-manifest.json
```

Evaluate timing accuracy:

```bash
uv run python scripts/analysis/evaluate_timing_accuracy.py .training/shotml-label-manifest.json --format table --json-output artifacts/timing-accuracy-summary.json
```

Optional automated pipeline:

```bash
uv run python scripts/analysis/run_auto_training_pipeline.py .training
```

Rules:
- Do not change thresholds blindly.
- Do not claim timing improvement without artifact proof.
- Do not modify training corpus files unless requested.
- Prefer small, reversible changes.
- Keep generated artifacts under artifacts/ unless the repo documents otherwise.
- Do not commit large media files or local training artifacts unless explicitly requested.

Done means:
- Relevant analysis tests pass.
- A preflight artifact or timing summary exists when behavior changed and sample data is available.
- Any missing sample/corpus dependency is stated clearly.
- Remaining detection/timing risks are reported.

Report:
Changed:
Verified:
Result:
Risks:
