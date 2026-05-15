# Scoring

This package owns scoring presets, per-shot score helpers, penalty handling, hit-factor math, and PractiScore import support.

## Purpose

Use it when the change affects ruleset behavior, score letters, penalty semantics, hit-factor calculation, or PractiScore-derived scoring context.

## Read This First

- [logic.py](logic.py)
- [practiscore.py](practiscore.py)

## Main Files

- [logic.py](logic.py): preset catalog, scoring calculations, score assignment, summary helpers
- [practiscore.py](practiscore.py): PractiScore parsing and normalization helpers
- [practiscore_sync_normalize.py](practiscore_sync_normalize.py), [practiscore_web_extract.py](practiscore_web_extract.py): remote artifact workflows

## Runtime Flow

1. Choose or infer a scoring preset.
2. Store per-shot score marks and penalties on the shared project.
3. Derive summary values for the browser shell, metrics, and overlay layers.

## Key Extension Points

- `apply_scoring_preset`
- `assign_score`
- `calculate_hit_factor`
- `calculate_scoring_summary`
- PractiScore import helpers

## Related Tests

- [../../../tests/scoring/](../../../tests/scoring/)
- [../../../tests/analysis/test_practiscore_import.py](../../../tests/analysis/test_practiscore_import.py)

## Related Docs

- [../../../docs/userfacing/panes/score.md](../../../docs/userfacing/panes/score.md)
- [../browser/README.md](../browser/README.md)
