# PROOF-T03-run1

- Task: `T03` — Bootstrap module shell
- Date: `2026-05-02`
- Owner: `copilot-orchestrator-20260502-t03-run1`
- Validation tier: `Tier B` (task packet override: exact required command was `uv run pytest tests/browser/test_browser_static_ui.py tests/browser/test_browser_control.py`)
- Result: `pass`

## Scope completed

- Validated the existing T03 bootstrap candidate in `src/splitshot/browser/static/index.html`, `src/splitshot/browser/static/app.js`, and `tests/browser/test_browser_static_ui.py`.
- Confirmed the shell now boots `app.js` with `<script type="module" src="/static/app.js?v=20260501f"></script>`.
- Kept the module-mode compatibility shim in `app.js` intentionally so existing browser tests and page-scope access patterns continue to work while later cleanup tasks retire the monolith globals.
- Confirmed the bootstrap candidate preserves initial project UI-state/tool application and keeps the null-safe file-input wiring in the owned `wireEvents()` seam.
- Left `tests/browser/test_browser_control.py` unchanged because the required validation scope passed without any T03 assertion updates there.
- Stayed out of forbidden hotspots: `src/splitshot/browser/static/styles.css`, `src/splitshot/browser/static/lib/**`, `src/splitshot/browser/static/components/**`, and `src/splitshot/browser/static/panes/**` were not modified.

## Validation performed

### Required command

The task packet required this exact command:

```text
uv run pytest tests/browser/test_browser_static_ui.py tests/browser/test_browser_control.py
```

The first attempt failed for an environment reason before the full scope could complete:

```text
FileNotFoundError: [Errno 2] No such file or directory: 'ffmpeg'
=========================== short test summary info ============================
FAILED tests/browser/test_browser_control.py::test_browser_state_exposes_metrics_after_primary_ingest - FileNotFoundError: [Errno 2] No such file or directory: 'ffmpeg'
...
======================== 23 failed, 69 passed in 46.99s ========================
```

### Environment repair used to enable the required command

The local shell did not have `ffmpeg` / `ffprobe` on `PATH`, and a Homebrew install was blocked by unwritable `/opt/homebrew` directories. To avoid changing tracked repo files, the repair used the project virtualenv only:

- installed `static-ffmpeg` into the configured `.venv` using environment package-install tooling
- exposed the virtualenv-local helpers as `ffmpeg` / `ffprobe`

Command used to expose the binaries on the project PATH:

```text
ln -sf static_ffmpeg .venv/bin/ffmpeg && ln -sf static_ffprobe .venv/bin/ffprobe && ls -l .venv/bin/ffmpeg .venv/bin/ffprobe
```

Verification command:

```text
uv run python - <<'PY'
import shutil
print(shutil.which('ffmpeg'))
print(shutil.which('ffprobe'))
PY
```

Verification result:

```text
/Volumes/Storage/GitHub/splitshot/.venv/bin/ffmpeg
/Volumes/Storage/GitHub/splitshot/.venv/bin/ffprobe
```

After the environment repair, the exact required command was rerun unchanged and passed:

```text
uv run pytest tests/browser/test_browser_static_ui.py tests/browser/test_browser_control.py
```

Passing result:

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.11, pytest-8.4.2, pluggy-1.6.0
PySide6 6.11.0 -- Qt runtime 6.11.0 -- Qt compiled 6.11.0
rootdir: /Volumes/Storage/GitHub/splitshot
configfile: pyproject.toml
plugins: cov-7.1.0, qt-4.5.0
collected 92 items

tests/browser/test_browser_static_ui.py .....................            [ 22%]
tests/browser/test_browser_control.py .................................. [ 59%]
.....................................                                    [100%]

======================== 92 passed in 609.77s (0:10:09) ========================
```

### Supplemental validation

While diagnosing the missing-media-tool issue, this narrower shell-contract command was also run and passed:

```text
uv run pytest tests/browser/test_browser_static_ui.py
```

Result:

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.11, pytest-8.4.2, pluggy-1.6.0
PySide6 6.11.0 -- Qt runtime 6.11.0 -- Qt compiled 6.11.0
rootdir: /Volumes/Storage/GitHub/splitshot
configfile: pyproject.toml
plugins: cov-7.1.0, qt-4.5.0
collected 21 items

tests/browser/test_browser_static_ui.py .....................            [100%]

============================== 21 passed in 1.22s ==============================
```

### Validation notes

- The exact Tier B command required by the T03 task packet was run and passed.
- No broader browser suite was run because the task packet explicitly narrowed T03 validation to the two owned browser files, and that required scope completed successfully.

## Audit performed

### Audit commands run

```text
wc -l src/splitshot/browser/static/app.js
```

```text
find src/splitshot/browser/static -maxdepth 2 -type f | sort
```

Attempted suggested command:

```text
rg '^let ' src/splitshot/browser/static/app.js
```

Fallback used because `rg` was not available in the shell:

```text
grep -c '^let ' src/splitshot/browser/static/app.js
grep '^let ' src/splitshot/browser/static/app.js | head -n 20
```

Ownership check:

```text
git status --short -- activedev/modularization/progress.md src/splitshot/browser/static/index.html src/splitshot/browser/static/app.js tests/browser/test_browser_static_ui.py tests/browser/test_browser_control.py activedev/modularization/proof/PROOF-T03-run1.md
git status --short -- src/splitshot/browser/static/styles.css 'src/splitshot/browser/static/lib' 'src/splitshot/browser/static/components' 'src/splitshot/browser/static/panes'
```

### Audit results

`app.js` size at T03 completion:

```text
15244 src/splitshot/browser/static/app.js
```

Static file layout at the T03 shell boundary:

```text
src/splitshot/browser/static/README.md
src/splitshot/browser/static/__init__.py
src/splitshot/browser/static/__pycache__/__init__.cpython-312.pyc
src/splitshot/browser/static/app.js
src/splitshot/browser/static/githublogo.png
src/splitshot/browser/static/index.html
src/splitshot/browser/static/logo.png
src/splitshot/browser/static/styles.css
```

Top-level `let` count fallback result:

```text
93
```

Final owned-path status:

```text
 M activedev/modularization/progress.md
 M src/splitshot/browser/static/app.js
 M src/splitshot/browser/static/index.html
 M tests/browser/test_browser_static_ui.py
?? activedev/modularization/proof/PROOF-T03-run1.md
```

Forbidden-hotspot status result:

```text

```

### Audit conclusion

- `T03` stayed within its owned shell/bootstrap boundary files.
- No forbidden-pane or stylesheet extraction work was introduced.
- The legacy-global compatibility shim is intentional, documented, and justified by the existing browser-test contract: many browser tests still access bare page-scope bindings/functions after load, which would otherwise break under `type="module"`.
- `app.js` did not shrink yet, but that is acceptable for `T03`; this task establishes the module bootstrap seam and compatibility layer so later extraction tasks can reduce the monolith safely.
- No cross-pane imports or early pane/module extraction were introduced.

## Remaining risks

- The module-mode compatibility shim in `app.js` is intentionally broad and should be retired only after later extraction/cleanup tasks replace the page-global browser contract.
- The validation repair added virtualenv-local `ffmpeg` / `ffprobe` helpers so the exact test command could pass in this worktree. Those environment changes are outside tracked repo files and may need to be repeated in a fresh worktree.
