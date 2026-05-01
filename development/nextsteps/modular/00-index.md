# Modular Architecture — Full Rewrite Plan

## Approach

The entire frontend is rewritten from scratch in a new directory `src2/`. The old `src/`
is never modified. When all phases complete, `src/` is archived and `src2/` takes its place.

```
Working directory: /Volumes/Storage/GitHub/splitshot

Phase 0:  src/  ──(copy all)──▶  src2/  ──(rebuild static/)──▶  src2/ (modular)
Phase 1-11:                     src2/  ──(add pane files)────▶  src2/ (panes added)
Phase 12:  src/  ──(archive)──▶  src-archive/
           src2/ ──(rename)───▶  src/ (final modular)
```

The only files ever modified live under `src2/splitshot/browser/static/` — the new
frontend modules. All backend Python code is copied verbatim.

## Phases

| Phase | File | New files created | Est. |
|-------|------|-------------------|------|
| [0](01-phase0-foundation.md) | Foundation | 25+ files: lib/, components/, widgets/, pane-base, app.js, index.html, styles/ | 4d |
| [1](02-phase1-settings-pane.md) | Settings pane | `panes/settings-pane.js` | 1d |
| [2](03-phase2-merge-pane.md) | Merge pane | `panes/merge-pane.js` | 1d |
| [3](04-phase3-metrics-pane.md) | Metrics pane | `panes/metrics-pane.js` | 1d |
| [4](05-phase4-project-pane.md) | Project pane | `panes/project-pane.js` | 2d |
| [5](06-phase5-export-pane.md) | Export pane | `panes/export-pane.js` | 1d |
| [6](07-phase6-review-pane.md) | Review pane | `panes/review-pane.js` | 1d |
| [7](08-phase7-shotml-pane.md) | ShotML pane | `panes/shotml-pane.js` | 1d |
| [8](09-phase8-overlay-pane.md) | Overlay pane | `panes/overlay-pane.js` | 2d |
| [9](10-phase9-scoring-pane.md) | Scoring pane | `panes/scoring-pane.js` | 2d |
| [10](11-phase10-markers-pane.md) | Markers pane | `panes/markers-pane.js` | 3d |
| [11](12-phase11-timing-pane.md) | Timing pane | `panes/timing-pane.js` | 3d |
| [12](13-phase12-swap.md) | Swap | Archive `src/`, rename `src2/` → `src/` | 1d |

## File location reference

```
Source (read-only):  /Volumes/Storage/GitHub/splitshot/src/splitshot/browser/static/
New directory:       /Volumes/Storage/GitHub/splitshot/src2/splitshot/browser/static/
```

Every "copy from app.js" reference in phase docs refers to:
```
/Volumes/Storage/GitHub/splitshot/src/splitshot/browser/static/app.js
```

Every "create file at X" means:
```
/Volumes/Storage/GitHub/splitshot/src2/splitshot/browser/static/X
```

## Verification approach

Each pane phase produces a self-contained module file. It is NOT loaded by the new
app.js bootstrap until Phase 12 (when all panes exist). Each phase's verification:

1. **Old tests still pass** — run the test suite against `src/` (old `static/` is
   untouched):
   ```bash
   uv run python scripts/testing/run_test_suite.py --mode all-together --format table
   ```
2. **New file is correct** — lint the new file:
   ```bash
   uvx ruff check src2/splitshot/browser/static/
   ```
3. **Integration test** — after Phase 12 only:
   ```bash
   cd /Volumes/Storage/GitHub/splitshot/src2
   uv run python scripts/testing/run_test_suite.py --mode all-together --format table
   ```

## Strategy for each new file

Every new JS module:
1. Is an ES module using `import`/`export`
2. Reads state from a `store` object (not from global `window.state`)
3. Writes to its own DOM elements
4. Has its own event wiring in `init()`
5. Has zero dependency on the old `app.js`
