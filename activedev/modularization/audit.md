# Modularization Audit Directions

Audit answers a different question than validation.

- **Validation:** does the app still work exactly the same?
- **Audit:** did the internal architecture actually improve according to the modularization design?

Both are required.

## Global structural rules

1. Pane modules must not import directly from other pane modules.
2. Shared behavior must move through backbone modules or shared components/widgets.
3. `app.js` must shrink over time toward bootstrap-only responsibility.
4. Legacy globals may remain temporarily only when the active task packet allows them as compatibility shims.
5. New module boundaries must align with `activedev/modular.md` and this program plan.
6. CSS splitting happens late; do not scatter styles early unless the task explicitly owns that work.
7. Zero UX drift remains in force even if validation passes.

## Ownership and overlap rules

A task run fails audit if it:

- edits a file not listed in the task's `touches-files`
- edits a file listed in the task's `forbidden-files`
- modifies another task's owned shared-test assertions without explicit handoff
- changes a hotspot while that hotspot is claimed by another active task

`progress.md` is the source of truth for active claims.

## Mandatory audit checks by phase

### Governance and baseline tasks (`T00`–`T02`)

- required control-plane files exist
- task ids and naming are consistent across `plan.md`, `progress.md`, task files, and proof files
- missing QA docs are either restored (`T02`) or explicitly recorded as blockers before code extraction begins

### Extraction tasks (`T03`–`T09E`)

- module boundaries match the assigned task
- no prohibited cross-pane imports were introduced
- owned tests/docs were updated in the same run when required
- compatibility shims are documented, not accidental
- `app.js` responsibility moved in the intended direction

### Cleanup and certification tasks (`T10`–`T12`)

- retired monolith paths are actually removed
- no ghost wrappers remain without purpose
- CSS is organized into the planned structure without selector drift
- final static asset layout supports future PWA shell work

## Suggested command checks

Use the smallest relevant subset for the task and record results in the proof file.

```text
wc -l src/splitshot/browser/static/app.js
find src/splitshot/browser/static -maxdepth 2 -type f | sort
rg 'from "\.\./panes/|from "\.\/.*pane' src/splitshot/browser/static/panes -g '*.js'
rg '^let ' src/splitshot/browser/static/app.js
```

The exact command list can expand once `T01` captures the ownership anchors.

## Shared hotspot audit map

| Hotspot | Audit owner expectations |
| --- | --- |
| `index.html` | only `T03` and later `T11` may touch shell/module/css wiring |
| `app.js` | active extraction task may touch only its owned anchor blocks |
| `styles.css` | remains single-owner until `T11` |
| shared browser tests | task packet must state which assertions or sections it owns |
| QA matrix/coverage docs | keep synchronized with test claims and control inventory |

## Ownership appendix

`T01` must update this section before `T03` starts.

### Required additions from `T01`

- exact current ownership anchors or line-range notes for `app.js`
- exact current ownership anchors or line-range notes for `index.html`
- exact current ownership anchors or selector blocks for `styles.css`
- exact mapping of shared test sections to `T09B`, `T09C`, `T09D`, and `T09E`

### Current state

Pending `T01` baseline truth audit.

## PWA-readiness audit targets

Modularization is successful only if the resulting structure makes future PWA work straightforward. The audit should verify that the architecture now supports:

- a module-based application shell
- clean static asset boundaries suitable for precache lists
- isolated storage and file-loading seams
- centralized browser API and state coordination
- deployment-friendly static organization for a later `manifest.json`, `sw.js`, and Cloudflare Pages hosting model

## Proof requirements

Every audit run recorded in a proof file must state:

- which audit checks were executed
- whether ownership boundaries were respected
- whether any compatibility shim remains intentionally
- whether architectural drift or overlap was detected
- whether the task passed audit, passed with risk, or failed
