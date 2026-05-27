# Completion Bundle Recovery Next Steps

This file is the short operational mirror of `MASTER_STATUS.md`.

Use `MASTER_STATUS.md` for the authoritative cross-bundle status board, normalized vocabulary, dependency map, and evidence model. Use this file for the ordered next-work queue only.

## Execution snapshot (`2026-05-26`)

- The completion program is now intended to close in exactly two work efforts:
  - Work Effort 1 / Set 1: `development/`
  - Work Effort 2 / Set 2: `testing/`
- The detailed source bundles and parity-input reference material now live under `predev/`.
- Work Effort 1 is now complete: `development/` closed DEV-301, republished its handoff, and passed the fresh all-together suite anchor.
- Work Effort 2 already inherits closed Stage and Match docs/test/proof/signoff plus partial Performance proof anchors.
- Work Effort 2 still owns the remaining Performance proof package, Backend and Modularization proof/signoff, the source `predev/tests/` bundle execution, screenshots/artifacts/docs sync, and final gates.
- Canonical repo proof anchor: `../../../artifacts/all-together.json` records `691 passed`, but that repo-health baseline still does not by itself close Work Effort 2.

Important distinction:

- source `predev/tests/` is the detailed lane for `TST-*` work
- aggregate `testing/` is the Work Effort 2 overlay
- they are not the same thing

## Two-work-effort recovery order

### Work Effort 1 / Set 1 — `development/`

Status: `done`; DEV-301 complete.

Preserve these handed-off implementation baselines unless a newly discovered blocker forces a documented reopen:

1. Preserve the settled Stage implementation baseline (`STG-001` through `STG-006`).
2. Preserve the settled Match implementation baseline (`MCH-001` plus implementation sides of `MCH-002` through `MCH-006`).
3. Preserve the settled Performance implementation baseline (`PRF-001` plus implementation sides of `PRF-002` through `PRF-005`).
4. Preserve the published Backend implementation handoff (`BEK-001` through `BEK-006`).
5. Preserve the published Modularization implementation handoff (`MOD-001` through `MOD-005`).
6. Preserve the published Work Effort 1 handoff and reopen `development/` only if Work Effort 2 finds a first-order implementation blocker.

### Work Effort 2 / Set 2 — `testing/`

Preserve this order unless a newly discovered blocker forces a documented change:

1. Close the remaining Performance shell/detail/search-filter/backup-export package and `PRF-007`.
2. Close Backend and Modularization signoff scope through `BEK-007`, `BEK-008`, `MOD-006`, and `MOD-007`.
3. Execute the entire source `predev/tests/` bundle scope (`TST-001` through `TST-009`).
4. Refresh screenshots, artifacts, QA docs, coverage docs, and user-facing docs where required.
5. Run focused proof slices, owned suites, the canonical full suite, and final visual signoff last.

## Guardrails

- Do **not** treat source `predev/tests/` and aggregate `testing/` as synonyms.
- Work Effort 1 is already handed to `testing/`; do **not** reopen it unless the issue is a real implementation blocker rather than proof-packaging or documentation work.
- Do **not** mark `testing/` complete until the relevant source-bundle final gates are actually closed.
- Do **not** treat broad validation runs as closure for Backend, Modularization, or the source `predev/tests/` bundle.
- If Work Effort 2 uncovers a real implementation blocker, reopen the relevant source bundle explicitly instead of hiding that blocker inside proof language.
- Keep `README.md`, this file, and `MASTER_STATUS.md` aligned on the same three-directory, two-work-effort model.
