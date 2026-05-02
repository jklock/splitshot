# Modularization Validation Directions

The goal of validation is to prove that modularization preserves the **exact current browser experience** while improving only internal architecture.

## Program invariant

A task is not complete if it causes visible UI drift, control drift, label drift, layout drift, workflow drift, or browser contract drift.

## Validation evidence sources

The program already has meaningful validation assets. Use them instead of inventing weaker substitutes.

| Asset | Purpose |
| --- | --- |
| `tests/browser/test_browser_static_ui.py` | static shell contract for HTML/CSS/JS expectations |
| `tests/browser/test_browser_control_inventory_audit.py` | control inventory contract backed by the coverage-plan docs |
| `tests/browser/test_browser_control_coverage_matrix.py` | browser QA matrix contract |
| `tests/browser/test_browser_interactions.py` | broad live interaction regression coverage |
| `tests/browser/test_merge_export_contracts.py` | merge/export contract validation |
| `tests/browser/test_overlay_review_contracts.py` | overlay/review contract validation |
| `tests/browser/test_timing_waveform_contracts.py` | timing/waveform contract validation |
| `scripts/audits/browser/run_browser_ui_surface_audit.py` | UI surface artifact generation |
| `scripts/audits/browser/run_browser_interaction_audit.py` | interaction artifact generation |
| `artifacts/browser-ui-surface-audit-latest.json` | current UI audit baseline |
| `artifacts/browser-interaction-audit-latest.json` | current interaction audit baseline |

## Preconditions

Before running a validation suite, confirm:

1. the task's dependencies are `done` in `progress.md`
2. required QA docs exist if the task depends on them (`T02` restores them)
3. the validation scope matches the task packet
4. the proof file will record the exact commands used

## Validation tiers

### Tier A — governance and documentation tasks (`T00`–`T02`)

Use the narrowest useful validation:

- verify required files exist and are linked correctly
- if QA docs were changed or restored, run the tests that depend on them
- if no product code changed, record why the full browser suite was not rerun

Suggested commands:

```text
uv run pytest tests/browser/test_browser_control_inventory_audit.py tests/browser/test_browser_control_coverage_matrix.py
```

### Tier B — bootstrap and backbone tasks (`T03`–`T07`)

Minimum validation:

```text
uv run pytest tests/browser/test_browser_static_ui.py
uv run pytest tests/browser/test_timing_waveform_contracts.py
uv run pytest tests/browser/test_overlay_review_contracts.py
```

Escalate to the broader browser suite when the task touches a shared hotspot or when the task packet requires it:

```text
uv run pytest tests/browser/
```

### Tier C — pane extraction tasks (`T08`–`T09E`)

Run the pane-specific tests named in the task packet. At minimum, include the relevant contract tests and the broader browser suite when shared interaction behavior changes.

Examples:

```text
uv run pytest tests/browser/test_scoring_metrics_contracts.py
uv run pytest tests/browser/test_project_lifecycle_contracts.py tests/browser/test_merge_export_contracts.py
uv run pytest tests/browser/test_overlay_review_contracts.py tests/browser/test_browser_interactions.py
```

### Tier D — cleanup, CSS split, and final certification (`T10`–`T12`)

These tasks require the strictest scope.

```text
uv run pytest tests/browser/
uv run python scripts/testing/run_test_suite.py --mode all-together --format table
uv run python scripts/audits/browser/run_browser_ui_surface_audit.py
uv run python scripts/audits/browser/run_browser_interaction_audit.py
```

If the task packet requires export or AV audits, include:

```text
uv run python scripts/audits/browser/run_browser_av_audit.py
uv run python scripts/audits/browser/run_browser_export_matrix.py
```

## Artifact review

When a task reruns an audit script, compare the resulting JSON or logged output against the current baseline artifacts:

- `artifacts/browser-ui-surface-audit-latest.json`
- `artifacts/browser-interaction-audit-latest.json`

Any difference must be explained in the proof file. “It changed because the refactor moved things around” is **not** an acceptable explanation if the user-visible UI is supposed to be identical.

## Manual smoke checklist

Automation is the primary gate, but the following must be manually confirmed during final certification or when a task packet calls it out:

- pane order in the rail is unchanged
- status bar copy and empty-state messaging are unchanged
- waveform, overlay, review, and export flows still feel identical
- PractiScore fallback workflow still exists
- settings/layout capture and release behavior is unchanged
- no new scroll glitches or pane-switch jumps were introduced

## Proof requirements

Every proof file must state:

1. which validation tier applied
2. the exact commands that were run
3. whether the full suite was run or intentionally deferred
4. the final pass/fail result for the required scope
5. any remaining risks

## Sign-off standard

The sign-off standard for this program is **100% pass rate on the required validation scope for the task and final certification suite**. This program does **not** claim 100% code coverage unless the measured coverage command actually reports that result.
