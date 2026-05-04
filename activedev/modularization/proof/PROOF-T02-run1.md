# PROOF-T02-run1

- Task: `T02` — QA baseline doc restoration
- Date: `2026-05-02`
- Owner: `copilot-orchestrator-20260502-t02-run1`
- Validation tier: `Tier A`
- Result: `pass`

## Scope completed

- Restored `docs/project/browser-control-qa-matrix.md`
- Restored `docs/project/browser-control-coverage-plan.md`
- Restored `docs/project/browser-full-e2e-qa-plan.md`
- Reconciled `docs/README.md`, `docs/project/DEVELOPING.md`, and `docs/tests/TEST_SUITE_GUIDE.md`
- Left product code and the two enforcing browser tests unchanged because the restored docs satisfied the existing contract

## Validation performed

### Required command

First attempt failed because the local workspace `.venv` was broken before T02 validation began:

```text
uv run pytest tests/browser/test_browser_control_inventory_audit.py tests/browser/test_browser_control_coverage_matrix.py
```

Failure observed:

```text
warning: Ignoring existing virtual environment linked to non-existent Python interpreter: .venv/bin/python3 -> python
Using CPython 3.12.11
error: failed to remove directory `/Volumes/Storage/GitHub/splitshot/.venv/lib`: Resource busy (os error 16)
```

### Environment repair used to enable the required command

```text
mv .venv .venv-broken-t02-20260502
uv sync --extra dev
```

After the repair, the required command was rerun exactly and passed:

```text
uv run pytest tests/browser/test_browser_control_inventory_audit.py tests/browser/test_browser_control_coverage_matrix.py
```

Passing result:

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.11, pytest-8.4.2, pluggy-1.6.0
PySide6 6.11.0 -- Qt runtime 6.11.0 -- Qt compiled 6.11.0
rootdir: /Volumes/Storage/GitHub/splitshot
configfile: pyproject.toml
plugins: cov-7.1.0, qt-4.5.0
collected 3 items

tests/browser/test_browser_control_inventory_audit.py ..                 [ 66%]
tests/browser/test_browser_control_coverage_matrix.py .                  [100%]

============================== 3 passed in 1.51s ===============================
```

### Validation notes

- The exact Tier A command required by the task packet was run and passed.
- No broader browser suite was rerun because `T02` changes only docs plus developer references, and `validation.md` explicitly scopes governance/doc tasks to the narrowest useful validation.

## Audit performed

### Audit commands run

```text
echo 'RESTORED_DOCS' ; for f in docs/project/browser-control-qa-matrix.md docs/project/browser-control-coverage-plan.md docs/project/browser-full-e2e-qa-plan.md; do if [ -f "$f" ]; then echo "present $f"; else echo "missing $f"; fi; done
```

```text
echo 'TASK_OWNED_PATH_STATUS' ; git status --short -- activedev/modularization/progress.md docs/README.md docs/project/DEVELOPING.md docs/project/browser-control-qa-matrix.md docs/project/browser-control-coverage-plan.md docs/project/browser-full-e2e-qa-plan.md docs/tests/TEST_SUITE_GUIDE.md tests/browser/test_browser_control_inventory_audit.py tests/browser/test_browser_control_coverage_matrix.py ; echo ; echo 'SRC_STATUS' ; git status --short -- src
```

### Audit results

Restored docs exist:

```text
RESTORED_DOCS
present docs/project/browser-control-qa-matrix.md
present docs/project/browser-control-coverage-plan.md
present docs/project/browser-full-e2e-qa-plan.md
```

Task-owned path status and product-code check:

```text
TASK_OWNED_PATH_STATUS
 M activedev/modularization/progress.md
 M docs/README.md
 M docs/project/DEVELOPING.md
 M docs/tests/TEST_SUITE_GUIDE.md
?? docs/project/browser-control-coverage-plan.md
?? docs/project/browser-control-qa-matrix.md
?? docs/project/browser-full-e2e-qa-plan.md

SRC_STATUS
```

### Audit conclusion

- The restored docs match current browser reality as documented from the live `index.html` shell and current browser suites.
- The enforcing tests and the restored docs agree.
- No product-code files under `src/` were touched by `T02`.
- The task stayed within its allowed file list.

## Remaining risks

- `docs/tests/TEST_SUITE_GUIDE.md` still has pre-existing markdown-lint findings outside the T02-edited lines; they were not widened into a formatting cleanup task.
- The workspace already contained unrelated pre-existing modifications outside T02 ownership (`activedev/00-index.md`, `activedev/modular.md`, `activedev/modularization/audit.md`, `activedev/modularization/orchestration-prompt.md`, and `activedev/modularization/plan.md`). This proof isolates only the T02-owned paths and confirms `src/` remained untouched.
