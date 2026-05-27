# Development Artifact Compatibility Note

## Purpose

This file is retained only so older links into `development/artifacts.md` do not break.

The active execution bundle now uses:

- `progress.md` for live task and blocker state
- `proof.md` for proof taxonomy and evidence obligations
- `outcome.md` for status and gate narrative

## Current policy

- Do **not** add new primary execution truth here.
- If an external reference still points at `artifacts.md`, direct it to the correct modern file.
- Only the integrator may update this compatibility note.

## Crosswalk

| Need | Primary file |
| --- | --- |
| live execution state | `progress.md` |
| proof classes and evidence requirements | `proof.md` |
| bundle status and gate narrative | `outcome.md` |
| execution rules | `spec.md`, `plan.md`, `tasks.md`, `orchestration.prompt.md` |

## Compatibility statement

The historical artifact-ledger role formerly carried by this file has been intentionally split across `progress.md`, `proof.md`, and `outcome.md` so parallel workers do not collide in one oversized mixed-purpose file.
