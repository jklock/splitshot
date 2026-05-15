# Scripts

This directory is the operational toolbox for SplitShot. Use it to bootstrap machines, run tests, audit browser behavior, inspect ShotML output, validate release readiness, and refresh documentation assets.

## Start Here

If you are new to the repo, read:

1. [../README.md](../README.md)
2. [../docs/project/DEVELOPING.md](../docs/project/DEVELOPING.md)
3. [../docs/tests/TEST_SUITE_GUIDE.md](../docs/tests/TEST_SUITE_GUIDE.md)

## Script Groups

| Path | Type | Use it for |
| --- | --- | --- |
| `setup/` | setup | Workstation or runner bootstrap |
| `testing/` | validation | Suite execution, CI-local checks, Electron preflight, packaged-app smoke |
| `audits/browser/` | audit | Browser UI, interaction, export, and AV validation |
| `analysis/` | analysis | ShotML inspection, corpus review, manifest generation, training prep, timing evaluation |
| `docs/` | docs | Documentation-support tasks such as screenshot capture |
| `export/` | reporting | Export-oriented CSV utilities |
| `tooling/` | validation | Local environment and toolchain checks |
| `release/` | release | Signing and release-side helpers |

## High-Value Entry Scripts

### Developer workflow

| Script | Type | What it does | When to use it | Inputs / outputs |
| --- | --- | --- | --- | --- |
| `testing/run_test_suite.py` | validation | Canonical grouped pytest runner | Any normal local validation run | Inputs: suite/mode flags. Outputs: console summary, optional raw or JSON artifact |
| `testing/run_ci_locally.py` | validation | Runs CI-shaped local job groups | Before pushing or when reproducing CI locally | Inputs: job name. Outputs: job summary and command failures |
| `testing/run_electron_preflight.py` | validation | Runs the local Electron release gate for the current platform | Before packaging or release workflow triggers | Inputs: local repo state. Outputs: preflight pass/fail |
| `tooling/validate_toolchain.py` | validation | Checks FFmpeg, browser assets, and packaged resources | New machines, runner health, setup debugging | Inputs: local toolchain. Outputs: console status lines |
| `docs/capture_browser_screenshots.py` | docs | Launches the app, seeds demo state, and regenerates the user-doc screenshot set | After browser UI changes or during doc refresh | Inputs: local fixtures. Outputs: refreshed files in `docs/screenshots/` |

### Browser audits

| Script | Type | What it does | When to use it | Inputs / outputs |
| --- | --- | --- | --- | --- |
| `audits/browser/run_browser_ui_surface_audit.py` | audit | Verifies UI-surface expectations against the running browser app | Browser-shell regressions or control audits | Inputs: app runtime. Outputs: audit summary |
| `audits/browser/run_browser_interaction_audit.py` | audit | Exercises real browser interactions against local media fixtures | Interaction regressions or evidence gathering | Inputs: media paths and optional PractiScore file. Outputs: structured audit report |
| `audits/browser/run_browser_av_audit.py` | audit | Checks audio/video playback and timeline stability | AV-specific browser regressions | Inputs: app runtime and media. Outputs: JSON/table audit summary |
| `audits/browser/run_browser_export_matrix.py` | audit | Exercises browser export combinations | Export-surface investigation | Inputs: export matrix parameters. Outputs: matrix results |

### Analysis and training

| Script | Type | What it does | When to use it | Inputs / outputs |
| --- | --- | --- | --- | --- |
| `analysis/analyze_video_shots.py` | analysis | Runs the analysis pipeline on one video and summarizes detected shots | Quick timing inspection on a candidate clip | Inputs: video path. Outputs: console summary, optional JSON artifact |
| `analysis/audit_training_corpus.py` | analysis | Audits a training corpus for quality and consistency | Corpus maintenance | Inputs: corpus root. Outputs: table or JSON audit |
| `analysis/bootstrap_training_manifest.py` | analysis | Builds or refreshes the review manifest from the corpus | Start of a labeling or training pass | Inputs: corpus root. Outputs: manifest JSON |
| `analysis/autolabel_training_manifest.py` | analysis | Promotes trusted detections into an auto-labeled tier | Review acceleration after manifest bootstrap | Inputs: manifest JSON. Outputs: updated manifest and optional summary |
| `analysis/evaluate_timing_accuracy.py` | analysis | Compares detector timestamps against reviewed labels across thresholds | Timing-quality evaluation | Inputs: manifest JSON. Outputs: table or JSON summary |
| `analysis/prioritize_training_review.py` | analysis | Ranks manifest entries for human review | Decide what to review next | Inputs: manifest JSON. Outputs: review queue JSON |
| `analysis/extract_training_dataset.py` | analysis | Converts manifest labels into a training dataset | Training prep | Inputs: manifest JSON. Outputs: NPZ dataset and optional summary |
| `analysis/train_audio_event_model_from_dataset.py` | analysis | Trains a candidate bundle from an extracted dataset | Model experiments | Inputs: NPZ dataset. Outputs: candidate bundle and training summary |
| `analysis/run_auto_training_pipeline.py` | analysis | Chains bootstrap, auto-label, dataset extraction, and candidate training | Unattended corpus-driven experiments | Inputs: corpus root. Outputs: manifest, dataset, bundle, summary artifacts |

## Common Commands

```bash
uv run python scripts/testing/run_test_suite.py --list
uv run python scripts/testing/run_test_suite.py --mode all-together --format table
uv run python scripts/testing/run_ci_locally.py --job source-local
uv run python scripts/testing/run_electron_preflight.py
uv run python scripts/docs/capture_browser_screenshots.py
uv run python scripts/tooling/validate_toolchain.py
uv run python scripts/analysis/analyze_video_shots.py /path/to/stage.mp4 --format table --json-output artifacts/shot-preview.json
uv run python scripts/audits/browser/run_browser_ui_surface_audit.py
```

## Read This Next

- [../docs/tests/TEST_SUITE_GUIDE.md](../docs/tests/TEST_SUITE_GUIDE.md)
- [../docs/project/ARCHITECTURE.md](../docs/project/ARCHITECTURE.md)
- [../src/splitshot/README.md](../src/splitshot/README.md)
