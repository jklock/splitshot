# Consistency Review Plan — SplitShot v1

This document is a concrete, actionable plan for bringing SplitShot to v1 consistency.
Every section lists specific items that need to change, with file:line references.

---

## Phase 1: Automated Lint & Format Baseline

### 1.1 Run `ruff check` and catalog all violations

```bash
uvx ruff check . 2>&1 | tee artifacts/ruff-check-baseline.txt
```

Expected findings based on current code:
- ~48 bare `except Exception` blocks, ~25 with `# noqa: BLE001` and ~23 without
- Any `F401` (unused import) or `F841` (unused variable) that may have accumulated
- `I` rule violations if import ordering is off

### 1.2 Run `ruff format --diff` and catalog all formatting deltas

```bash
uvx ruff format . --diff 2>&1 | tee artifacts/ruff-format-diff.txt
```

Since `pyproject.toml` sets `line-length = 100` but `ruff format` has never been run in CI,
expect non-trivial formatting drift (line breaks, trailing commas, indentation).

**Action required:**
- Run `uvx ruff format .` to apply all formatting changes in one pass
- Add `ruff format` to CI workflow (`.github/workflows/ci.yml`)

### 1.3 Fix bare `except Exception` blocks without `# noqa: BLE001`

23 blocks lack the `# noqa: BLE001` suppression comment. These will be flagged by ruff
once the `BLE` ruleset is active. Fix by either:
- Narrowing the caught exception type, OR
- Adding `# noqa: BLE001` if broad catch is intentional

**Files affected:**

| File | Lines | Count |
|------|-------|-------|
| `src/splitshot/scoring/practiscore_web_extract.py` | 546, 586, 605, 668, 682, 706 | 6 |
| `src/splitshot/browser/practiscore_session.py` | 102, 111, 149, 225, 242, 298, 329, 381, 394, 404, 406, 421, 425 | 13 |
| `src/splitshot/browser/practiscore_qt_runtime.py` | 140, 290, 406 | 3 |
| `src/splitshot/browser/practiscore_browser_cookies.py` | 30, 49 | 2 |

**Action:** Change each to either narrow the exception type or add `# noqa: BLE001`.

### 1.4 Review silent `except Exception: pass` blocks as highest-risk items

These swallow errors with no logging or fallback. Most concerning:

| File | Line | Concern |
|------|------|---------|
| `src/splitshot/browser/practiscore_session.py` | 419, 423 | Silent failure to close runtime/Playwright — leaks browser processes |
| `src/splitshot/browser/practiscore_qt_runtime.py` | 404 | Swallows `goto()` navigation failure — user sees broken session |
| `src/splitshot/browser/practiscore_session.py` | 404, 406 | Nested pattern in cookie sync swallows all errors |

**Action:** Add logging via `activity.log()` before each `pass`, or restructure to propagate
errors upward.

---

## Phase 2: Naming & Import Consistency

### 2.1 Fix private import boundary violation

One instance of a module importing a private (`_`-prefixed) symbol from another module:

- **`src/splitshot/analysis/training_dataset.py:10`**
  `from splitshot.analysis.corpus import _load_aligned_audio`

**Action:** Either:
- Make `_load_aligned_audio` public (rename to `load_aligned_audio`) if it's a legitimate cross-module dependency, OR
- Inline the functionality in `training_dataset.py` to remove the cross-module dependency.

### 2.2 Add or remove `__all__` consistently across all modules

Currently only `src/splitshot/__init__.py` defines `__all__`. No subpackage or submodule does.

**Action:** Choose one convention and apply it project-wide:

- **Option A (add `__all__` everywhere):** Define `__all__` in every submodule to explicitly list public API symbols.
  - `src/splitshot/domain/models.py` — list all dataclasses and top-level functions
  - `src/splitshot/analysis/detection.py` — list public detection functions
  - `src/splitshot/analysis/corpus.py` — list `Group`, `Article`, etc.
  - All 15 subpackage `__init__.py` files — add re-exports of key symbols
- **Option B (remove `__all__` everywhere):** Delete `__all__` from `src/splitshot/__init__.py`.

**Recommendation:** Option A — define `__all__` on every submodule to establish a clean public v1 API surface.

### 2.3 Re-export key symbols in subpackage `__init__.py` files

Currently all 15 subpackage `__init__.py` files are docstring-only stubs. Consumers must know
exact submodule paths. For v1, establish convenience imports:

**Examples:**
```python
# src/splitshot/domain/__init__.py
from splitshot.domain.models import Project, ShotEvent, VideoAsset
__all__ = ["Project", "ShotEvent", "VideoAsset"]
```

```python
# src/splitshot/analysis/__init__.py
from splitshot.analysis.detection import detect_beep, detect_shot
__all__ = ["detect_beep", "detect_shot"]
```

Each subpackage should re-export its 3–10 most important public symbols.

### 2.4 Replace `print()` with structured logging in non-CLI modules

9 `print()` calls exist in non-CLI modules:

| File | Lines |
|------|-------|
| `src/splitshot/browser/server.py` | 520, 521, 529, 530, 543, 548, 560, 561 |
| `src/splitshot/browser/activity.py` | 86 (part of logging infra — acceptable) |

**Action:** Replace the 8 calls in `server.py` with `self.activity.log(...)` calls so they
go through the structured logging system. The `activity.py` call is acceptable as it is
part of the logging infrastructure.

---

## Phase 3: Code Structure & Architecture Consistency

### 3.1 Eliminate duplicated serialization code

`_popup_template_from_dict` and `_badge_style_from_dict` are each defined in both
`domain/models.py` AND `config.py` with subtle behavioral differences.

**`_popup_template_from_dict` — duplicated across:**

| Aspect | `config.py:53` | `domain/models.py:837` |
|--------|---------------|------------------------|
| `quadrant` | Raw string via `str(payload.get(...))` | Normalized via `_normalize_popup_bubble_quadrant(...)` |
| `opacity` | Clamped via `_float_or_default` helper | Clamped inline via `max(0.0, min(1.0, ...))` |

**`_badge_style_from_dict` — duplicated across:**

| Aspect | `config.py:78` | `domain/models.py:607` |
|--------|---------------|------------------------|
| Fallback support | Yes — second arg `fallback: BadgeStyle \| None` | No fallback |
| Opacity clamping | `max(0.0, min(1.0, _float_or_default(...)))` | **Not clamped** — potential bug |
| String coercion | Explicit `str()` calls | Implicit string via `.get()` default |

**Action:**
1. Remove the `config.py` versions (`_popup_template_from_dict` and `_badge_style_from_dict`)
2. Import the `domain/models.py` versions in `config.py`
3. Merge the best behaviors: add fallback support to `domain/models.py`'s `_badge_style_from_dict`,
   ensure both versions clamp opacity, both normalize quadrant

### 3.2 Audit `dataclasses.asdict()` vs `_serialize()` divergence

The main project serialization path uses `_serialize()` (domain/models.py:576), which handles
`Enum` → value, `datetime` → isoformat, `Path` → str. Meanwhile, 15+ `dataclasses.asdict()` calls
in `ui/controller.py`, `browser/state.py`, `analysis/auto_labeling.py`, `analysis/review_queue.py`,
`analysis/corpus.py`, and `scoring/logic.py` bypass this and return native Python objects.

**Risk:** If any dataclass gains a `datetime`, `Path`, or nested `Enum` field, `asdict()` will
produce non-JSON-serializable dicts silently.

**Action:**
- Audit every `asdict()` call site (listed in exploration as ~15 locations)
- For each, verify the dataclass has NO `datetime`, `Path`, or nested `Enum` fields
- Add a comment at each call site documenting why `asdict()` is safe there, OR
- Replace `asdict()` calls with `_serialize()` where the dataclass could gain such fields

### 3.3 Register `from __future__ import annotations` on 16 `__init__.py` files

All 57 source files already have it (41 non-`__init__` do, 16 `__init__` do not).
Since the `__init__.py` files contain only docstrings with no type hints, this is
low-risk but worth completing for hygiene.

**Action:** Add `from __future__ import annotations` after the docstring in all 16 files:
- `src/splitshot/__init__.py`
- `src/splitshot/{analysis,benchmarks,browser,browser/static,domain,export,media,merge,overlay,persistence,presentation,resources,scoring,timeline,ui}/__init__.py`

### 3.4 Add ruff rule selection to `pyproject.toml`

Currently `pyproject.toml` sets only `line-length = 100` with no explicit `[tool.ruff.lint]`
section, meaning ruff defaults apply. For v1 consistency, explicitly select rules:

```toml
[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "BLE", "RUF"]
ignore = ["BLE001"]   # suppress broad-exception globally instead of per-line noqa

[tool.ruff.format]
quote-style = "double"
```

This eliminates the need for 25 `# noqa: BLE001` annotations and catches import-ordering
issues via `I`.

---

## Phase 4: Test Consistency

### 4.1 Rename test files for naming convention consistency

Files that deviate from the `test_<module>_<scenario>.py` convention:

**Files with bare `test_<module>.py` (no scenario qualifier):**

| Current Name | Suggested Name |
|---|---|
| `tests/analysis/test_analysis.py` | `tests/analysis/test_analysis_detection.py` |
| `tests/cli/test_cli.py` | Already acceptable (single-module test) |
| `tests/export/test_export.py` | `tests/export/test_export_pipeline.py` |
| `tests/media/test_media_toolchain.py` | (already has qualifier — OK) |
| `tests/persistence/test_persistence.py` | `tests/persistence/test_persistence_projects.py` |
| `tests/presentation/test_presentation.py` | `tests/presentation/test_presentation_stage.py` |

**Files using "and" in name (bundled concept):**

| Current Name | Suggested Name |
|---|---|
| `tests/scoring/test_scoring_and_merge.py` | Split into `tests/scoring/test_scoring_logic.py` and `tests/merge/test_merge_layouts.py` |

### 4.2 Move cross-package test files to correct directories

12 test files live in `tests/browser/` but their names reference non-browser modules:

| Current Location | References Module | Should Move To |
|---|---|---|
| `tests/browser/test_overlay_review_contracts.py` | overlay | `tests/presentation/` or combine |
| `tests/browser/test_merge_export_contracts.py` | merge/export | `tests/export/` (duplicate exists!) |
| `tests/browser/test_project_lifecycle_contracts.py` | persistence | `tests/persistence/` (duplicate exists!) |
| `tests/browser/test_scoring_metrics_contracts.py` | scoring | `tests/scoring/` (duplicate exists!) |
| `tests/browser/test_settings_defaults_truth_gate.py` | config | `tests/cli/` or new `tests/config/` |
| `tests/browser/test_settings_e2e.py` | config | `tests/cli/` or new `tests/config/` |
| `tests/browser/test_metrics_e2e.py` | presentation | `tests/presentation/` |
| `tests/browser/test_timing_waveform_contracts.py` | timeline | `tests/timeline/` (create dir) |
| `tests/browser/test_practiscore_sync_controller.py` | scoring | `tests/scoring/` |
| `tests/analysis/test_practiscore_web_extract.py` | scoring | Move to `tests/scoring/` |
| `tests/analysis/test_practiscore_sync_normalize.py` | scoring | Move to `tests/scoring/` |
| `tests/analysis/test_practiscore_import.py` | scoring | Move to `tests/scoring/` |

**Action:** Move each file and update any internal import paths or pytest references.

### 4.3 Resolve duplicate test filenames across directories

Three test filenames exist in two directories each:

| Filename | Path 1 (browser/e2e) | Path 2 (module-specific) |
|---|---|---|
| `test_merge_export_contracts.py` | `tests/browser/` | `tests/export/` |
| `test_project_lifecycle_contracts.py` | `tests/browser/` | `tests/persistence/` |
| `test_scoring_metrics_contracts.py` | `tests/browser/` | `tests/scoring/` |

**Action:** For each pair, decide:
- Are they testing the same thing? If so, merge into the module-specific directory.
- Are they testing different aspects? If so, rename the browser copy to include "e2e"
  (e.g., `test_merge_export_contracts.py` → `test_merge_export_e2e_contracts.py`).

### 4.4 Add test files for uncovered source modules

The following source modules have no dedicated test file:

| Source Module | Notes |
|---|---|
| `src/splitshot/analysis/audio_features.py` | Audio feature extraction — test with synthetic audio |
| `src/splitshot/analysis/ml_runtime.py` | ONNX ML inference — may need model file; at minimum test init |
| `src/splitshot/analysis/model_bundle.py` | Model packaging — can test with mocked resources |
| `src/splitshot/analysis/sync.py` | Sync offset computation — critical timing logic |
| `src/splitshot/browser/practiscore_browser_cookies.py` | Cookie loading — test with mock browser_cookie3 |
| `src/splitshot/browser/practiscore_profile.py` | Profile management — test with tmp_path |
| `src/splitshot/domain/models.py` | Core domain — test serialization round-trip, validation |
| `src/splitshot/media/audio.py` | Audio extraction — test with synthetic WAV |
| `src/splitshot/media/thumbnails.py` | Thumbnail generation — test with synthetic video |
| `src/splitshot/ui/controller.py` | Core controller — large module, currently only tested indirectly |
| `src/splitshot/utils/time.py` | Time utilities — small, quick to add |

**Action:** Create basic test files for at minimum `domain/models.py` (serialization round-trip),
`analysis/sync.py` (offset computation), and `media/audio.py` (audio extraction) before v1.

---

## Phase 5: Configuration & Tooling Consistency

### 5.1 Add `ruff format` to CI workflow

Current `ci.yml` runs `ruff check` but not `ruff format`.

**Action:** Add to `.github/workflows/ci.yml`:
```yaml
- name: Check formatting
  run: uvx ruff format . --check
```

### 5.2 Add explicit ruff configuration sections

Current `pyproject.toml`:
```toml
[tool.ruff]
line-length = 100
```

**Action:** Expand to:
```toml
[tool.ruff]
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "BLE", "RUF"]
ignore = ["BLE001"]

[tool.ruff.format]
quote-style = "double"
```

### 5.3 Remove stale `ui/widgets/` directory

The directory `src/splitshot/ui/widgets/` exists but contains only `__pycache__/`
(compiled `.pyc` files for `waveform_editor`, `overlay_preview`, etc.). No source `.py` files
exist. The source was presumably deleted or migrated.

**Action:** Delete `src/splitshot/ui/widgets/` entirely (including `__pycache__/`).

---

## Phase 6: Formatting & Style Deep-Dive

### 6.1 Verify quote-style consistency

The codebase overwhelmingly uses double-quoted strings (99.9%+). The only exceptions are
~8 single-quoted strings in `src/splitshot/browser/server.py` that intentionally embed
double-quote characters without escaping.

**Action:** After enabling `[tool.ruff.format] quote-style = "double"`, `ruff format`
will normalize any inconsistent quoting. Verify the diff is clean.

### 6.2 Verify blank-line conventions

- 2 blank lines before class definitions
- 1 blank line before function definitions (not methods)
- 1 blank line after imports, before first function/class

**Action:** `ruff format` handles this automatically once run.

---

## Phase 7: Manual Deep-Dive (Sampling)

### 7.1 Representative file deep-reads

Select 5 files spanning different modules and sizes for manual review:

| File | Size | Module |
|------|------|--------|
| `src/splitshot/domain/models.py` | 1401 lines (large) | Domain |
| `src/splitshot/scoring/practiscore.py` | 682 lines (medium) | Scoring |
| `src/splitshot/presentation/popups.py` | ~400 lines (medium) | Presentation |
| `src/splitshot/analysis/sync.py` | ~200 lines (small) | Analysis |
| `src/splitshot/utils/time.py` | ~50 lines (small) | Utils |

**For each file, check:**
- `-> None` annotation on every void function (no missing return types)
- No commented-out code blocks
- Consistent `if`/`elif`/`else` structure (no single-line ifs without braces where multi-line used elsewhere)
- `"string"` vs `'string'` consistency (should all be double quotes after Phase 6)
- No bare `assert` statements in non-test code (use `if not x: raise ...` instead)

### 7.2 API response shape audit

`src/splitshot/browser/server.py` has ~100+ API route handlers. Spot-check 10–15 for:

- **Consistent response envelope**: All routes should return `{"ok": true, "data": ...}` or
  `{"ok": false, "error": "..."}` consistently. Check for any routes returning raw data.
- **Consistent error format**: Error responses should all include `"error"` string.
- **Consistent HTTP method usage**: GET for reads, POST for mutations, PUT for updates, DELETE for removals.
- **Consistent parameter naming**: `shot_id` vs `shotId` vs `shotID` — pick one.

### 7.3 Browser test organization audit

`tests/browser/` has 17 files (213 test functions) — the largest test directory.

- Check for duplicated test setup logic across files (could be extracted to fixtures)
- Check for test helper functions that exist in multiple files (extract to `tests/browser/conftest.py`)
- Verify Playwright page fixture exists at the right scope

### 7.4 JavaScript/CSS file audit

`src/splitshot/browser/static/app.js` (13,064 lines) and `styles.css` (4,066 lines) are
very large single files. For v1:

- Check for obvious dead code (commented-out blocks, unreachable functions)
- Check for hardcoded URLs or API paths that should be constants
- CSS: check for unused selectors and duplicated rule blocks
- `index.html` is embedded in JS `app.js` — consider extracting to a real file

---

## Execution Order

| Phase | Effort | Risk | Quick Wins First |
|-------|--------|------|------------------|
| 1.1–1.2 (ruff baseline) | Low | None | ✅ Immediate |
| 1.3 (BLE001 noqa) | Low | None | ✅ Immediate |
| 2.4 (print → log) | Low | Low | ✅ Immediate |
| 3.3 (__future__ on __init__) | Low | None | ✅ Immediate |
| 5.3 (remove stale widgets/) | Low | None | ✅ Immediate |
| | | | |
| 2.1 (private import) | Medium | Low | |
| 2.2–2.3 (__all__ + re-exports) | Medium | Medium | |
| 3.1 (dedup serialization) | Medium | Medium | |
| 3.2 (asdict audit) | Medium | Low | |
| 3.4 (ruff config) | Low | Low | |
| 5.1–5.2 (CI format) | Low | Low | |
| | | | |
| 4.1–4.3 (test reorg) | High | Medium | Last |
| 4.4 (add test coverage) | High | Low | Last |
| 6 (format deep-dive) | Medium | None | |
| 7 (manual review) | Medium | N/A | Ongoing |

---

## Success Criteria

Before v1 release, the following must be clean:
1. `uvx ruff check .` — zero violations
2. `uvx ruff format . --check` — zero diffs
3. No bare `except Exception` without `# noqa` or specific exception type
4. No private cross-module imports
5. All subpackage `__init__.py` files re-export public API
6. No duplicated serialization logic
7. Test files follow `test_<module>_<scenario>.py` convention in the correct directory
8. At minimum `domain/models.py` and `analysis/sync.py` have dedicated test files
9. No `print()` calls in non-CLI modules
10. Stale `ui/widgets/` directory removed
