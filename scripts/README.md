# Scripts

SplitShot scripts are organized by purpose so users can find setup, validation, analysis, and export helpers without scanning one flat directory.

## Layout

- `scripts/setup/`: workstation bootstrap for macOS, Linux, and Windows PowerShell.
- `scripts/testing/`: master test runner and related testing helpers.
- `scripts/audits/browser/`: real browser validation scripts for UI surface, AV playback, interaction flows, and export matrices.
- `scripts/analysis/`: ShotML and analysis helpers, including preflight split/confidence inspection and training-corpus audits.
- `scripts/export/`: export-oriented utilities such as benchmark CSV generation.
- `scripts/tooling/`: local environment and toolchain validation.

## Common Commands

```bash
uv run python scripts/testing/run_test_suite.py --list
uv run python scripts/testing/run_test_suite.py --mode one-by-one --format table --raw-output artifacts/test-run.raw.txt
uv run python scripts/testing/run_test_suite.py --mode all-together --format json --json-output artifacts/test-run.json
uv run python scripts/testing/run_electron_preflight.py
uv run python scripts/testing/run_ci_locally.py --job source-local
uv run python scripts/testing/run_ci_locally.py --job browser-local
uv run python scripts/testing/run_ci_locally.py --job electron-release-local
powershell -ExecutionPolicy Bypass -File scripts/setup/setup_self_hosted_runner_windows.ps1
bash scripts/setup/setup_self_hosted_runner_linux.sh
uv run python scripts/analysis/analyze_video_shots.py /path/to/stage.mp4 --format table --json-output artifacts/shot-preview.json
uv run python scripts/analysis/audit_training_corpus.py .training --format table --json-output artifacts/training-corpus-audit.json
uv run python scripts/analysis/bootstrap_training_manifest.py .training --output .training/shotml-label-manifest.json
uv run python scripts/analysis/autolabel_training_manifest.py .training/shotml-label-manifest.json --summary-output artifacts/training-autolabel-summary.json
uv run python scripts/analysis/evaluate_timing_accuracy.py .training/shotml-label-manifest.json --format table --json-output artifacts/timing-accuracy-summary.json
uv run python scripts/analysis/prioritize_training_review.py .training/shotml-label-manifest.json --json-output artifacts/training-review-queue.json
uv run python scripts/analysis/extract_training_dataset.py .training/shotml-label-manifest.json --output artifacts/training-dataset-verified.npz
uv run python scripts/analysis/extract_training_dataset.py .training/shotml-label-manifest.json --output artifacts/training-dataset.npz --use-detector-drafts --detector-draft-policy review-clean --augment-replicas-per-event 2
uv run python scripts/analysis/train_audio_event_model_from_dataset.py artifacts/training-dataset.npz --output-bundle artifacts/model_bundle_candidate.py --summary-output artifacts/model-training-summary.json --class-weighting balanced
uv run python scripts/analysis/run_auto_training_pipeline.py .training --manifest-output .training/shotml-label-manifest.json --dataset-output artifacts/training-dataset-auto.npz --output-bundle artifacts/model_bundle_candidate_auto.py --training-summary-output artifacts/model-training-auto-summary.json
uv run python scripts/audits/browser/run_browser_ui_surface_audit.py
uv run python scripts/audits/browser/run_browser_interaction_audit.py
uv run python scripts/tooling/validate_toolchain.py
```

## Notes

- The master test runner supports per-suite execution, one-file-at-a-time runs, combined runs, and raw or JSON output artifacts.
- `scripts/testing/run_ci_locally.py` is the local-first gate runner. It owns the source-local suites, browser-local suite, and the local Electron release preflight before any GitHub Actions workflow is triggered.
- `scripts/testing/run_electron_preflight.py` is the local release-critical Electron gate. Run it before any Electron workflow trigger. It owns the source-side checks that do not belong in the packaging workflow: runtime check, bundle verification, launch-intent unit tests, headless backend tests, parity audit, source smoke, current-platform smoke build, and packaged-app launch.
- The Electron packaging workflow now targets the self-hosted Windows and Linux runners by labels and keeps macOS on `macos-14`. Use the `Runner Smoke` workflow to validate those appliances after host changes.
- `scripts/setup/setup_self_hosted_runner_windows.ps1` and `scripts/setup/setup_self_hosted_runner_linux.sh` are idempotent host-prep scripts for the existing self-hosted runners. They install only missing prerequisites, locate the existing runner service, and start it if needed.
- The video preflight analysis helper uses the same ShotML detection path as the application and is intended to help choose a starting sensitivity slider value before import.
- The timing accuracy evaluator compares detected beep, split, last-shot, and stage-time timestamps against accepted manifest labels across a threshold sweep. It uses manual verified labels first and accepted auto-consensus labels when manual labels are absent.
- The training corpus audit helper now also reports shot-pass disagreement and duplicate-stage consistency so repeated recordings can be compared for count drift.
- The label-manifest bootstrap helper writes detector-draft beep and shot labels into a reviewable JSON manifest and preserves existing manual review fields when the manifest is regenerated.
- The auto-label helper promotes accepted manifest entries into an `auto_labeled` tier without misreporting those clips as manual verified labels. The detector's primary start beep and shot timeline remain the anchor; tone/model passes refine confidence and consensus but should not replace a close first-pass timeline.
- The training review prioritizer ranks manifest entries by how quickly they can produce trustworthy actuals, promotes one representative clip per duplicate stage, and pushes clipping or shot-disagreement cases behind cleaner first-pass review candidates.
- The training dataset extractor turns a reviewed manifest into a compressed NPZ feature dataset for real-footage retraining, with optional detector-draft fallback for early experiments. It now records whether each extracted row came from verified labels, automated consensus labels, or detector drafts, and the default detector-draft path is review-clean rather than blindly trusting every draft row.
- The training dataset extractor now supports deterministic waveform augmentation for beep and shot windows so early experiments can better cover gain shifts, noise, filtering, and clipping without changing serving-time feature extraction.
- The unattended auto-training pipeline bootstraps the manifest, auto-labels stable clips, extracts a trusted auto-consensus dataset, and trains a candidate bundle in one command so corpus-driven tuning can run without manual review in the loop.
- The dataset trainer builds a candidate MLP bundle from extracted NPZ features without overwriting the shipped model by default; it now supports balanced class weighting, early stopping, per-class validation recall, and separate verified-validation metrics so automated or draft-only runs do not get confused with actual reviewed-label performance.
- The CI browser gate uses the maintained `tests/browser/` Playwright-backed pytest suite. The standalone browser audit scripts remain available for deeper manual audits, and they now synthesize deterministic local MP4 fixtures if the default stage videos are missing.

**Last updated:** 2026-05-06
**Referenced files last updated:** 2026-05-06
