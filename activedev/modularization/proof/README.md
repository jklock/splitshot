# Proof Records

This directory stores immutable proof files for modularization task runs.

## Naming

Use this format:

- `PROOF-T00-run1.md`
- `PROOF-T09B-run2.md`
- `PROOF-T12-run1.md`

## Rules

1. Never overwrite an earlier proof file.
2. Failed retries get a new run number.
3. Each proof file must link back to the task id in `tasks/` and the status entry in `progress.md`.
4. Proof files must include validation results, audit results, and a final verdict.

The first real proof file for this program should document completion of `T00`.
