# Completion Bundle Recovery Next Steps

This file is the short operational mirror of `MASTER_STATUS.md`.

Use `MASTER_STATUS.md` for the authoritative cross-bundle status board, normalized vocabulary, dependency map, and evidence model. Use this file for the ordered next-work queue only.

## Execution snapshot (`2026-05-25`)

- The completion program is now intended to close in exactly two work efforts:
  - Work Effort 1 / Set 1: `development/`
  - Work Effort 2 / Set 2: `testing/`
- The detailed source bundles and parity-input reference material now live under `predev/`.
- Work Effort 1 already inherits materially advanced Stage, Match, and Performance implementation scope.
- Work Effort 2 already inherits Stage docs/test/proof sync plus partial Match and Performance proof anchors.
- Backend and Modularization implementation passes are now published for Work Effort 1 handoff; only the source `predev/tests/` bundle still needs its dedicated execution pass inside the two-effort model.
- Canonical repo proof anchor: `../../../artifacts/current-all-together.json` shows the current full-suite baseline passing with `649 passed`, but that baseline does not close either aggregate work effort by itself.

Important distinction:

- source `predev/tests/` is the detailed lane for `TST-*` work
- aggregate `testing/` is the Work Effort 2 overlay
- they are not the same thing

## Two-work-effort recovery order

### Work Effort 1 / Set 1 — `development/`

Preserve this order unless a newly discovered blocker forces a documented change:

1. Preserve the settled Stage implementation baseline (`STG-001` through `STG-006`).
2. Preserve the settled Match implementation baseline (`MCH-001` plus implementation sides of `MCH-002` through `MCH-006`).
3. Preserve the settled Performance implementation baseline (`PRF-001` plus implementation sides of `PRF-002` through `PRF-005`).
4. Preserve the published Backend implementation handoff (`BEK-001` through `BEK-006`).
5. Preserve the published Modularization implementation handoff (`MOD-001` through `MOD-005`).
6. Keep the handoff from `development/` into `testing/` published unless a new first-order implementation blocker is discovered.

### Work Effort 2 / Set 2 — `testing/`

Preserve this order unless a newly discovered blocker forces a documented change:

1. Close the remaining Match lifecycle and shell-convergence proof tied to `MCH-002`, `MCH-003`, `MCH-004`, and `MCH-006`.
2. Close Stage testing/signoff scope through `STG-007` and `STG-008`.
3. Close the remaining Match recap/composite/export artifact package and `MCH-007`.
4. Close the remaining Performance shell/detail/search-filter/backup-export package and `PRF-007`.
5. Close Backend and Modularization signoff scope through `BEK-007`, `BEK-008`, `MOD-006`, and `MOD-007`.
6. Execute the entire source `predev/tests/` bundle scope (`TST-001` through `TST-009`).
7. Refresh screenshots, artifacts, QA docs, coverage docs, and user-facing docs where required.
8. Run focused proof slices, owned suites, the canonical full suite, and final visual signoff last.

## Guardrails

- Do **not** treat source `predev/tests/` and aggregate `testing/` as synonyms.
- Do **not** mark `development/` complete until only testing/proof/signoff work remains.
- Do **not** mark `testing/` complete until the relevant source-bundle final gates are actually closed.
- Do **not** treat broad validation runs as closure for Backend, Modularization, or the source `predev/tests/` bundle.
- If Work Effort 2 uncovers a real implementation blocker, reopen the relevant source bundle explicitly instead of hiding that blocker inside proof language.
- Keep `README.md`, this file, and `MASTER_STATUS.md` aligned on the same three-directory, two-work-effort model.
