# T12 — Final Certification and PWA Readiness

## Metadata

| Field | Value |
| --- | --- |
| task-id | `T12` |
| status | tracked in `progress.md` |
| depends-on | `T10`, `T11` |
| parallel-lane | `none` |
| risk | `high` |
| touches-files | `activedev/00-index.md`, `activedev/modular.md`, `activedev/modularization/plan.md`, `activedev/modularization/progress.md`, `activedev/modularization/audit.md`, `src/splitshot/browser/static/README.md`, `docs/project/ARCHITECTURE.md`, `docs/project/browser-control-qa-matrix.md`, `activedev/modularization/proof/PROOF-T12-runN.md` |
| forbidden-files | `src/splitshot/browser/static/app.js`, `src/splitshot/browser/static/panes/**`, `src/splitshot/browser/static/components/**`, `src/splitshot/browser/static/lib/**`, `src/splitshot/browser/static/styles/**` unless a blocker forces a separately documented follow-up |
| owned-tests-docs | final documentation reconciliation plus all required validation and audit outputs |
| proof-file | `activedev/modularization/proof/PROOF-T12-runN.md` |

## Goal

Certify that the frontend is fully modularized, still behavior-identical to the baseline, and architecturally ready for the later PWA work.

## Scope

In scope:

- reconcile source docs with the final modular architecture
- run the final required validation and audit stack
- confirm proof completeness and task-board completeness
- record explicit PWA-readiness findings tied to the future PWA documents

Out of scope:

- shipping a service worker, manifest, or install UX
- new product behavior

## Preconditions

- [ ] `T10` and `T11` are `done`
- [ ] all prior proof files exist
- [ ] no open blockers remain in `progress.md`

## Implementation checklist

- [ ] reconcile `00-index.md` and `modular.md` with the completed program
- [ ] update technical docs that describe the new static/browser architecture
- [ ] run the final validation and audit suites
- [ ] certify whether the codebase is ready for the later PWA program

## Validation

Use Tier D from `validation.md`.

Required commands:

```text
uv run pytest tests/browser/
uv run python scripts/testing/run_test_suite.py --mode all-together --format table
uv run python scripts/audits/browser/run_browser_ui_surface_audit.py
uv run python scripts/audits/browser/run_browser_interaction_audit.py
```

Add AV/export audits if the final state or prior proofs show they are needed for sign-off.

## Audit checks

Use cleanup/certification checks from `audit.md`:

- task board is complete
- proof set is complete
- final architecture matches the modular design
- future PWA seams are present without shipping PWA behavior now

## Handoff outputs

- final certification proof
- reconciled source and technical docs
- explicit PWA-readiness statement for the next program

## Done criteria

- [ ] final validation suite passes at the required scope
- [ ] final audit passes
- [ ] docs reflect the completed architecture
- [ ] proof file was written
- [ ] `progress.md` was updated
