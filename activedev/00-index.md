# Active Development Document Index

This directory holds active planning and reference docs for the SplitShot modularization
effort (post-v1). The work lives on the `modularization` branch.

The directory now has two roles:

- **source documents** — the durable architectural narrative and future-state reference
- **execution control plane** — the operational docs that let subagents run the refactor safely

Modularization is explicitly a **zero-functional-change internal refactor**. The UI, workflow,
labels, layout, control ids, and overall experience must remain identical while the browser
frontend is restructured for long-term maintainability and later PWA work.

## Primary Documents

| File | Scope |
| --- | --- |
| [modular.md](modular.md) | **Architecture plan** — current state of the monolith, target modular architecture with backbone/panes/components, migration strategy, and risk mitigation. |
| [modularization/plan.md](modularization/plan.md) | **Program plan** — end-to-end execution map, constraints, dependencies, hotspots, and sign-off rules. |

## Operational Control Plane

The executable modularization program lives under [`modularization/`](modularization/).

| File | Scope |
| --- | --- |
| [modularization/progress.md](modularization/progress.md) | Rolling task ledger, locks, proof links, and blocker log. |
| [modularization/orchestration-prompt.md](modularization/orchestration-prompt.md) | Standard prompt and operating rules for subagent runs. |
| [modularization/validation.md](modularization/validation.md) | Required zero-UX-delta validation directions. |
| [modularization/audit.md](modularization/audit.md) | Structural audit rules, ownership checks, and PWA-readiness gates. |
| [modularization/tasks/](modularization/tasks/) | Non-overlapping task packets from governance through final certification. |
| [modularization/proof/](modularization/proof/) | Immutable proof records for each run. |

## Approach

The current plan (detailed in `modular.md`) is **in-place extraction**: each module is carved
out of the existing `app.js` monolith and moved to its own file, with the old code kept running
until the new module is ready to take over. The `src/` directory is modified in place.

Execution is governed by the task packets in `modularization/tasks/`, not by ad hoc edits.
Those task packets enforce file ownership, proof writing, validation, and audit requirements so
subagents can work in parallel without overlapping edits.

### Previous approach (abandoned)

An earlier plan proposed a **full rewrite in `src2/`** with phased creation of 25+ module
files followed by a directory swap. This was never started — `src2/` does not exist, and
the phase-specific sub-documents (`01-phase0-*.md` through `13-phase12-*.md`) were never
written. The in-place extraction in `modular.md` supersedes this approach.

## Current codebase snapshot (v1.0.0)

| File | Size | Description |
| --- | --- | --- |
| `src/.../static/index.html` | 1,194 lines | HTML shell with `<script>` tag (not module) |
| `src/.../static/app.js` | 14,376 lines | Monolithic JS — 0 imports, 0 classes, ~740 functions |
| `src/.../static/styles.css` | 4,587 lines | Single CSS file |
| `src/.../browser/server.py` | 1,712 lines | 42 route handlers + 13 utility endpoints |
| `src/.../browser/state.py` | 227 lines | Single function builds full state dict |
| `tests/browser/` | 226 test functions | Playwright-based browser test suite |

## Supporting Docs

| File | Scope |
| --- | --- |
| [backlog/backlog.md](backlog/backlog.md) | Feature backlog |
| [backlog/consistency.md](backlog/consistency.md) | Pre-v1 consistency review plan (completed) |
| [PWA/pwa-after-modularization.md](PWA/pwa-after-modularization.md) | PWA considerations post-modularization |
| [cloudflare/cloudflare-pages.md](cloudflare/cloudflare-pages.md) | Cloudflare Pages deployment notes |

## Program status

As of 2026-05-02, the modularization control workspace has been initialized under
`activedev/modularization/`. The next required gates are:

1. baseline truth audit (`T01`)
2. restoration of the missing browser QA/coverage docs (`T02`)
3. module-shell bootstrap (`T03`)

## Verification

Run the existing test suite against the unmodified monolith after any modularization work:

```bash
uv run python scripts/testing/run_test_suite.py --mode all-together --format table
```

Lint new module files:

```bash
uvx ruff check src/splitshot/browser/static/
```
