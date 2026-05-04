# PROOF-T01-run1

## Run metadata

| Field | Value |
| --- | --- |
| task-id | `T01` |
| run-id | `run1` |
| date | `2026-05-02` |
| branch | `modularization` |
| verdict | `pass` |

## Scope

This run verified the live-repository baseline facts for the monolithic browser shell, replaced stale estimates in the owned source docs with audited actuals, and populated the ownership appendix required before `T03` can start.

## Changed files

- `activedev/00-index.md`
- `activedev/modular.md`
- `activedev/modularization/plan.md`
- `activedev/modularization/audit.md`
- `activedev/modularization/progress.md`
- `activedev/modularization/proof/PROOF-T01-run1.md`

## Validation tier

Tier A — governance and documentation task.

## Validation performed

### Commands run

#### Live repo fact check

```text
cd /Volumes/Storage/GitHub/splitshot && printf 'BRANCH\n' && git rev-parse --abbrev-ref HEAD && printf '\nLINE_COUNTS\n' && wc -l src/splitshot/browser/static/index.html src/splitshot/browser/static/app.js src/splitshot/browser/static/styles.css src/splitshot/browser/server.py src/splitshot/browser/state.py && printf '\nBROWSER_TEST_FILES\n' && find tests/browser -maxdepth 1 -type f -name 'test_*.py' | sort && printf '\nBROWSER_TEST_FILE_COUNT\n' && find tests/browser -maxdepth 1 -type f -name 'test_*.py' | wc -l && printf '\nMISSING_QA_DOCS\n' && for f in docs/project/browser-control-qa-matrix.md docs/project/browser-control-coverage-plan.md docs/project/browser-full-e2e-qa-plan.md; do if [[ -e "$f" ]]; then printf 'present %s\n' "$f"; else printf 'missing %s\n' "$f"; fi; done
```

#### Browser test function inventory

```text
cd /Volumes/Storage/GitHub/splitshot && python3 - <<'PY'
from pathlib import Path
count = 0
per_file = []
for path in sorted(Path('tests/browser').glob('test_*.py')):
    text = path.read_text()
    file_count = sum(1 for line in text.splitlines() if line.startswith('def test_'))
    per_file.append((str(path), file_count))
    count += file_count
print('BROWSER_TEST_FUNCTION_COUNT')
print(count)
print('\nBROWSER_TEST_FUNCTIONS_PER_FILE')
for path, file_count in per_file:
    print(f'{file_count:4d} {path}')
PY
```

#### `app.js` audited-count and seam scan

```text
cd /Volumes/Storage/GitHub/splitshot && python3 - <<'PY'
from pathlib import Path
import re
from collections import defaultdict

app_path = Path('src/splitshot/browser/static/app.js')
lines = app_path.read_text().splitlines()
imports = [i for i,l in enumerate(lines,1) if re.match(r'^\s*import\b', l)]
exports = [i for i,l in enumerate(lines,1) if re.match(r'^\s*export\b', l)]
classes = [i for i,l in enumerate(lines,1) if re.match(r'^\s*class\b', l)]
lets = [i for i,l in enumerate(lines,1) if re.match(r'^let\s+', l)]
funcs = []
for i,l in enumerate(lines,1):
    m = re.match(r'^(?:async\s+)?function\s+([A-Za-z0-9_]+)\s*\(', l)
    if m:
        funcs.append((i, m.group(1)))
print('APP_AUDIT_COUNTS')
print(f'import_statements={len(imports)}')
print(f'export_statements={len(exports)}')
print(f'class_definitions={len(classes)}')
print(f'mutable_global_lets={len(lets)}')
print(f'named_function_declarations={len(funcs)}')
for target in ['render', 'wireEvents', 'setActiveTool', 'callApi', 'syncLocalProjectUiState']:
    found = [line for line,name in funcs if name == target]
    print(f'{target}_line={found[0] if found else "missing"}')
for target in ['render', 'wireEvents', 'setActiveTool', 'callApi', 'syncLocalProjectUiState']:
    found = [(idx, line) for idx, (line, name) in enumerate(funcs) if name == target]
    if found:
        idx, start = found[0]
        end = funcs[idx + 1][0] - 1 if idx + 1 < len(funcs) else len(lines)
        print(f'{target}_range={start}-{end}')
PY
```

#### HTML/CSS/shared-test anchor scan

```text
cd /Volumes/Storage/GitHub/splitshot && python3 - <<'PY'
from pathlib import Path
import re

index_path = Path('src/splitshot/browser/static/index.html')
index_lines = index_path.read_text().splitlines()
index_patterns = [
    ('stylesheet_link', '<link rel="stylesheet" href="/static/styles.css'),
    ('tool_rail', '<aside class="tool-rail"'),
    ('review_stack', '<section class="review-stack"'),
    ('timing_workbench', '<section id="timing-workbench"'),
    ('metrics_workbench', '<section id="metrics-workbench"'),
    ('scoring_workbench', '<section id="scoring-workbench"'),
    ('markers_workbench', '<section id="markers-workbench"'),
    ('pane_review', 'data-tool-pane="review"'),
    ('pane_metrics', 'data-tool-pane="metrics"'),
    ('pane_timing', 'data-tool-pane="timing"'),
    ('pane_shotml', 'data-tool-pane="shotml"'),
    ('pane_overlay', 'data-tool-pane="overlay"'),
    ('pane_markers', 'data-tool-pane="markers"'),
    ('pane_merge', 'data-tool-pane="merge"'),
    ('pane_export', 'data-tool-pane="export"'),
    ('pane_settings', 'data-tool-pane="settings"'),
    ('pane_project', 'data-tool-pane="project"'),
    ('script_tag', '<script src="/static/app.js'),
]
print('INDEX_HTML_ANCHORS')
for label, needle in index_patterns:
    for i, line in enumerate(index_lines, 1):
        if needle in line:
            print(f'{label}={i}')
            break

styles_path = Path('src/splitshot/browser/static/styles.css')
styles_lines = styles_path.read_text().splitlines()
style_patterns = [
    ('theme_root', ':root {'),
    ('shell_grid', '.cockpit-shell {'),
    ('tool_rail', '.tool-rail {'),
    ('status_bar', '.status-bar {'),
    ('review_grid', '.review-grid {'),
    ('video_stage', '.video-stage {'),
    ('live_overlay', '.live-overlay {'),
    ('popup_overlay', '.popup-overlay {'),
    ('waveform_panel', '.waveform-panel {'),
    ('tool_pane', '.tool-pane {'),
    ('shotml_section', '.shotml-section {'),
    ('metrics_summary_grid', '.metrics-summary-grid {'),
    ('review_visibility_manager', '.review-visibility-manager {'),
    ('responsive_900', '@media (max-width: 900px) {'),
]
print('\nSTYLES_CSS_ANCHORS')
for label, needle in style_patterns:
    for i, line in enumerate(styles_lines, 1):
        if line.strip() == needle.strip():
            print(f'{label}={i}')
            break

print('\nSHARED_TEST_FUNCTIONS')
for rel in [
    'tests/browser/test_merge_export_contracts.py',
    'tests/browser/test_overlay_review_contracts.py',
    'tests/browser/test_browser_interactions.py',
    'tests/browser/test_project_lifecycle_contracts.py',
    'tests/browser/test_timing_waveform_contracts.py',
]:
    path = Path(rel)
    print(f'[{rel}]')
    for i, line in enumerate(path.read_text().splitlines(), 1):
        m = re.match(r'^def\s+(test_[A-Za-z0-9_]+)\s*\(', line)
        if m:
            print(f'{i:5d} {m.group(1)}')
PY
```

#### Exact range computation for shared test sections and HTML/CSS blocks

```text
cd /Volumes/Storage/GitHub/splitshot && python3 - <<'PY'
from pathlib import Path
import re

for rel in [
    'tests/browser/test_merge_export_contracts.py',
    'tests/browser/test_overlay_review_contracts.py',
    'tests/browser/test_browser_interactions.py',
    'tests/browser/test_project_lifecycle_contracts.py',
    'tests/browser/test_timing_waveform_contracts.py',
]:
    path = Path(rel)
    lines = path.read_text().splitlines()
    tests = []
    for i, line in enumerate(lines, 1):
        m = re.match(r'^def\s+(test_[A-Za-z0-9_]+)\s*\(', line)
        if m:
            tests.append((i, m.group(1)))
    print(f'[{rel}]')
    for idx, (start, name) in enumerate(tests):
        end = tests[idx + 1][0] - 1 if idx + 1 < len(tests) else len(lines)
        print(f'{start}-{end} {name}')
    print()
PY
```

### Verified results

| Fact | Result |
| --- | --- |
| Git branch | `modularization` |
| `index.html` line count | 1,194 |
| `app.js` line count | 14,376 |
| `styles.css` line count | 4,587 |
| `server.py` line count | 1,712 |
| `state.py` line count | 227 |
| Browser test files | 18 |
| Browser test functions | 225 |
| Missing QA docs | `docs/project/browser-control-qa-matrix.md`, `docs/project/browser-control-coverage-plan.md`, and `docs/project/browser-full-e2e-qa-plan.md` are all missing |
| `app.js` imports / exports / classes | 0 / 0 / 0 |
| `app.js` top-level `let` globals | 91 |
| `app.js` named `function` declarations | 739 |
| `render()` seam | lines 12731–12747 |
| `wireEvents()` seam | lines 13763–14376 |

### Validation notes

- Only planning/control docs and the new proof file changed in this run. No `src/`, `tests/`, or QA-supporting doc-path files were edited.
- Under `validation.md` Tier A, direct fact verification was sufficient and the browser suite was intentionally **not** rerun.
- The missing QA-doc status was recorded explicitly so `T02` can restore those files before any validation step that depends on them; `T03` remains gated by that existing dependency rather than by a new `T01` blocker.

## Audit performed

### Audit checks executed

- Confirmed `T00` is already `done` and the control workspace is in place.
- Confirmed `T01` stayed within its allowed file list and did not edit any forbidden `src/`, `tests/`, or browser QA-doc files.
- Populated the ownership appendix in `activedev/modularization/audit.md` with exact `app.js`, `index.html`, `styles.css`, and shared browser test anchors.
- Partitioned the shared browser test sections for `T09B`, `T09C`, `T09D`, and `T09E`, with explicit boundary notes for the `T09C`/`T09D` and `T07`/`T09E` seams.
- Confirmed the missing QA docs remain tracked work for `T02`; `T03` is still gated by that existing dependency rather than by a new `T01` blocker.
- Updated `progress.md` so `T01` no longer holds the active claim after proof creation.

### Audit result

`pass`

## Follow-up for next task

`T02` should restore the missing browser QA/coverage docs named in this proof, then hand off to `T03` for the bootstrap module shell with the ownership appendix as the overlap-control map.

## Remaining risks

- `activedev/modular.md` still contains pre-existing markdown-lint findings outside the T01-edited facts; this run did not widen scope to clean the whole document.
- The `T09C`/`T09D` review-versus-overlay seam is now documented, but any future run that needs to edit both zones in `app.js` or the shared tests must keep a single active owner for that file during the run.
