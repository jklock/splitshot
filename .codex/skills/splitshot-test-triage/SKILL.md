---
name: splitshot-test-triage
description: Use SplitShot's canonical test runner to verify changes, isolate failures, and triage failing suites with the repo's existing uv/pytest workflow.
---
Use this skill when:
- Any SplitShot change needs verification.
- CI fails.
- A test suite fails locally.
- Core Python modules, browser code, export/media paths, or controller logic changed.
- The manager asks to test, verify, or triage failures.

Default approach:
- Use the repo's canonical test orchestrator first.
- Then narrow to direct pytest only after the failing area is known.
- Do not invent new test commands.
- Do not skip proof.

Commands:
Bootstrap only when dependencies are missing:

```bash
uv sync --extra dev
```

Install Playwright browsers only when browser tests or audits require them:

```bash
uv run python -m playwright install chromium firefox webkit
```

Run the canonical suite:

```bash
uv run python scripts/testing/run_test_suite.py --mode all-together --format table
```

If failures occur, isolate with JSON output:

```bash
uv run python scripts/testing/run_test_suite.py --mode one-by-one --format json --json-output artifacts/test-run.json --stop-on-failure
```

Then run the failing target directly:

```bash
uv run pytest tests/<path>/test_foo.py -k <expression>
```

Browser-specific verification:

```bash
uv run pytest tests/browser/
```

Analysis-specific verification:

```bash
uv run pytest tests/analysis/
```

Done means:
- The relevant suite passes, or the exact failing suite/test is identified.
- Any failing command is reported with the command, failure area, and likely cause.
- Browser UI/server/controller changes include browser-specific verification.
- The final report includes proof.

## Token Budget

Testing can be expensive. Minimize output.

Rules:

- Run targeted tests before broad suites.
- Use `--format table` or `--json-output artifacts/...` when available.
- Do not include full logs in responses.
- Summarize failures by suite, test name, and key error only.
- Do not rerun unchanged failures.
- Escalate to full suite only after targeted checks pass or when requested.

Report:
Changed:
Verified:
Result:
Risks:
