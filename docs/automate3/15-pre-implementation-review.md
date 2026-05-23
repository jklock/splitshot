> **Note:** Historical audit. Not a current readiness gate.


# Pre-Implementation Review

> **Status:** This review's feedback was incorporated into the planning package on 2026-05-21. The package is now ready for implementation subject to Phase 0 execution. This document is retained as an audit trail.
>
> **Written:** 2026-05-21
> **Scope:** `docs/automate3/` and `docs/automate3-ui/`

---

## 1. Executive Summary

The Automate3 planning package is a **sound product brief** but a **weak build specification**. The vision (four distinct, integrated frontend views), the naming contract, and the quality bar are all correct. However, the package contains **factually false claims**, **dangerously thin technical detail**, and **no migration strategy** for an 11,500-line frontend and a 24-test browser suite. If an agent starts building now, it will make hundreds of inconsistent micro-decisions, break existing tests without knowing which ones matter, and likely ship a half-working UI it believes is complete.

**This document exists to harden the plan into an exacting build specification before any implementation begins.**

---

## 2. Factually Wrong — Must Be Fixed First

### 2.1 Screenshot Artifact Claims Are False

**Affected files:**
- `docs/automate3/01-current-state-audit.md`
- `docs/automate3-ui/artifacts/current-screenshot-audit.md`
- `docs/automate3-ui/progress.md`
- `docs/automate3/14-truth-audit-matrix.md`

**Claim:** "Audited on 2026-05-21 from a launched browser app and fresh screenshots" with references to `artifacts/ui-audit-2026-05-21/contact-sheet.png`, `fresh-00-landing.png`, etc.

**Repo truth:** `artifacts/ui-audit-2026-05-21/` **does not exist**. Zero files found.

**Fix:** Replace all language implying these screenshots exist with:
> "Screenshot artifacts were referenced in planning but not found in the repo. They must be generated as the first action of Phase 0 before any implementation work proceeds."

---

### 2.2 Backend API Contract Hides Stub / Incorrect Implementations

**Affected file:** `docs/automate3/07-api-and-backend-contract.md`

**Claim:** Routes are listed with status "Requires verification," implying they are likely complete and only need a quick check.

**Repo truth:** Several routes are **partially or misleadingly implemented** and will mislead an implementation agent.

| Route | What the plan implies | What the code actually does |
|---|---|---|
| `/api/workspace/apply-from-first` | Copies Stage 1 settings to all siblings | Sets a `first_stage_snapshot` metadata blob and flips `inherited_from_first = True`. It **does not** copy actual output profiles, overlay settings, or export settings from Stage 1's project to sibling stages. |
| `/api/workspace/apply-from-first/preview` | Shows a diff of settings and conflicts | Returns a list of stage IDs with `will_inherit` based only on whether `override_values` is empty. It does **not** diff actual settings or show conflicts. |
| `/api/library/backup/create` | Creates a persisted backup | Returns an in-memory JSON manifest. It **does not write to disk**. |
| `/api/library/backup/restore` | Restores library from backup | Accepts a manifest and returns counts. It **does not write anything** to the library store. |
| `/api/landing/recent` | Returns Stage, Match, and Library records | Scans `~/.splitshot/projects` for `project.json` files and returns only entries with `type: "stage"`. It **does not** return Match or Library records. |

**Fix:** Rewrite the API contract table to include a **"Repo Truth"** column documenting the exact current payload shape, behavior, and known gaps for every route. Add a new section **"Routes With Known Backend Gaps"** listing the five routes above with the specifics above copied verbatim.

---

### 2.3 Truth Audit Matrix Is Too Vague to Be Useful

**Affected file:** `docs/automate3/14-truth-audit-matrix.md`

**Claim:** Six rows say "Routes appear present / Payload/UI fit requires verification."

**Repo truth:** Verification was performed. The matrix should record what was found.

**Fix:** Replace vague status entries with specific evidence:

- **Workspace routes:** `new_workspace`, `open_workspace`, `save_workspace`, `workspace_add_stage`, `workspace_remove_stage`, `workspace_open_stage`, `workspace_return_to_workspace`, `workspace_set_defaults`, `workspace_set_stage_override`, `workspace_reset_stage_override` all exist on `ProjectController` (lines 1002–1149) and are wired in `server.py`.
- **Angle director routes:** `angle_director_plan`, `angle_director_generate`, `angle_director_override_cut` exist in `controller.py` (lines 2068–2130) and `server.py`. `angle_director_plan` returns a dict whose keys are **not documented**.
- **Output profile routes:** `output_profile_list`, `create`, `update`, `delete`, `render` exist in `controller.py` (lines 1575–1730) and `server.py`. Note: `proxy_refresh` calls `output_profile_render("")` with an empty string, which looks suspicious and needs investigation.
- **Library routes:** `read_stage_metrics`, `read_match_metrics`, `compute_analytics` exist in `persistence/library.py`. They operate on JSONL files that are **empty on a fresh install**.

---

## 3. Missing Detail — Must Be Added Before Implementation

### 3.1 No DOM Restructuring Plan

**Affected files:** `docs/automate3/08-technical-architecture.md`, `docs/automate3-ui/spec.md`, all track docs

**Problem:** The current `index.html` is a single monolithic document (~1200 lines) containing the landing page, shared shell (tool rail, status bar, surface switcher, automation panels), video preview, waveform, inspector, and every tool pane. The plan says "split into four separate frontend views" but does not specify **how**.

**Fix:** Create `docs/automate3-ui/artifacts/dom-restructure-plan.md` with this exact mapping:

| Current Element | ID / Class | Target View |
|---|---|---|
| Landing | `#landing-page` | **Landing Page** (already separate, needs polish) |
| Tool rail | `.tool-rail` | **Stage only** — hidden in Match and Library |
| Cockpit root | `#cockpit-root` | **Stage Video Edit** — contains `.review-grid`, video, waveform, inspector |
| Automation panel (single) | `[data-surface-panel="single"]` | **Stage Video Edit** — becomes integrated output/multi-angle area |
| Automation panel (multi) | `[data-surface-panel="multi"]` | **Match Video Edit** — becomes match workspace body |
| Automation panel (library) | `[data-surface-panel="library"]` | **Performance Library** — becomes library dashboard body |
| Surface switcher | `.surface-header` | **Shell** — becomes global view switcher, not a tab inside cockpit |
| Status bar | `.status-bar` | **Shell** — global, shown in all views |
| Processing bar | `#processing-bar` | **Shell** — global, shown when needed |

Target DOM structure:
```html
<div class="app-shell">
  <header class="shell-header">...global context...</header>
  <div id="view-root">
    <!-- Only one child visible at a time -->
    <section id="view-landing">...</section>
    <section id="view-stage">...preview/timeline/inspector/output...</section>
    <section id="view-match">...header/grid/defaults/recap/composite...</section>
    <section id="view-library">...tiles/table/detail/analytics...</section>
  </div>
</div>
```

---

### 3.2 No Per-File Change Map

**Affected file:** `docs/automate3/08-technical-architecture.md`

**Problem:** "Likely files to change" is a flat list. An 11,500-line `app.js` needs a surgical map.

**Fix:** Create `docs/automate3-ui/artifacts/file-change-map.md`:

| File | Current Role | Exact Change |
|---|---|---|
| `index.html` | Monolithic DOM | Restructure into view containers per DOM plan; hide tool rail outside Stage; remove global automation strip from shell |
| `app.js` | Single init + all handlers | Extract view-specific renderers (`renderLanding()`, `renderStage()`, `renderMatch()`, `renderLibrary()`); add `activeView` state machine; preserve existing pane init logic |
| `lib/shell-runtime.js` | Layout + resize | Add view mounting/unmounting; preserve local state (scroll position, selection) on view switch |
| `lib/api.js` | API wrappers | Add wrappers for new dedicated routes; preserve existing mutation batching |
| `lib/store.js` | Backbone store | Add `activeView` to store schema |
| `styles.css` / `styles/*.css` | Existing styles | Add `.view-stage`, `.view-match`, `.view-library` scoped layout classes; retire global automation strip styles where appropriate |
| `panes/*.js` | Stage tool panes | Keep as-is; ensure they mount inside `#view-stage` only |
| `server.py` | Route dispatcher | Verify all new routes are registered; fix `apply-from-first` logic gap |
| `tests/browser/*` | Existing tests | Must all continue to pass; add new tests for view switching |

---

### 3.3 No State Management Integration Plan

**Affected file:** `docs/automate3/06-data-model-and-state-contract.md`

**Problem:** Lists `active_view` and `opened_from_match` as concepts but does not specify how they integrate with the existing `browser_state()` function or the frontend `appStore`.

**Fix:** Add this appendix to the state contract:

> **State Integration Rules**
>
> 1. `active_view` must be added to the payload returned by `browser_state()` in `src/splitshot/browser/state.py`.
> 2. The frontend `appStore` must include `activeView` in its schema with default `"landing"`.
> 3. `active_view` values: `"landing"`, `"stage"`, `"match"`, `"library"`.
> 4. `opened_from_match` and `return_to_match` must be derived from `controller.workspace` state:
>    - `opened_from_match = controller.workspace is not None and controller.project.workspace_id is not None`
>    - `return_to_match = { available: opened_from_match, workspace_id: controller.workspace.id if opened_from_match else None }`
> 5. View-local state retention:
>    - **Match**: scroll position and selected stage in grid → `localStorage` key `splitshot.match.gridState`
>    - **Stage**: active tool pane → `localStorage` key `splitshot.activeTool` (already exists)
>    - **Library**: selected record ID and active filters → `localStorage` key `splitshot.library.state`
>    - **Export progress**: in-memory only, not persisted across reloads

---

### 3.4 No CSS / Visual Design Token Specification

**Affected files:** `docs/automate3-ui/spec.md`, `docs/automate3-ui/tracks/01-current-ui-audit-and-visual-standard.md`

**Problem:** Says "professional dark visual treatment" but defines no exact values. Existing CSS is split across 7 files (`styles.css`, `styles/theme.css`, `styles/layout.css`, `styles/panes.css`, `styles/components.css`, `styles/widgets.css`, `styles/landing.css`).

**Fix:** Create `docs/automate3-ui/artifacts/visual-design-contract.md`:

```
Color Palette (dark-only, no light mode support)
- Background deepest:   #0b0d10   (app root)
- Background deep:      #111318   (view surfaces, cards)
- Background surface:   #181b21   (panels, tables, inputs)
- Border subtle:        #2a2e36   (dividers, card borders)
- Text primary:         #e8ecf1   (headings, labels)
- Text secondary:       #9ba3af   (hints, metadata)
- Accent:               #3b82f6   (primary actions, active states)
- Accent hover:         #2563eb
- Success:              #22c55e
- Warning:              #f59e0b
- Error:                #ef4444

Spacing Scale (4px base)
- xs: 4px, sm: 8px, md: 12px, lg: 16px, xl: 24px, 2xl: 32px

Typography
- Stack: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif
- Mono:  "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace
- H1: 24px / 700, H2: 18px / 600, H3: 15px / 600, Body: 13px / 400, Label: 11px / 500 uppercase

Control Tokens
- Button height: 32px (standard), 40px (primary)
- Input height: 32px, border-radius 4px
- Focus ring: 2px solid Accent with 2px offset
- Card border-radius: 6px
- Card padding: 16px

View Background Differentiation
- Landing: gradient from #0b0d10 to #111318 with subtle hero treatment
- Stage:   flat #111318 (editor workspace)
- Match:   flat #13151a (slightly distinct from Stage)
- Library: flat #0f1115 (dashboard feel)
```

---

### 3.5 No Migration Strategy

**Affected file:** `docs/automate3-ui/execution-order.md`

**Problem:** Step 2 says "Split shell and view architecture." Step 3 says "Landing Page." But restructuring `index.html` and `app.js` will break the app for intermediate commits.

**Fix:** Update the execution order with this phased migration:

> **Phase 1a — Wrap:** Add `activeView` state and view-container wrappers in `index.html`. Do **not** remove any existing elements. Use CSS (`[hidden]` or `.view-hidden`) to show/hide views. Verify existing tests pass.
>
> **Phase 1b — Move:** Move automation panels (`data-surface-panel="*"`) into their respective view containers using the new wrappers. Verify.
>
> **Phase 1c — Hide:** Hide `.tool-rail` in Match and Library views. Verify.
>
> **Phase 1d — Retire:** Only now remove the global automation strip from the shell. Verify.
>
> **Phase 2+ — Build:** Construct individual views inside their containers.

This ensures the app is never broken for more than one verified commit.

---

### 3.6 No Test Preservation Requirements

**Affected files:** `docs/automate3-ui/tracks/10-proof-regression-and-release.md`, `docs/automate3/10-acceptance-and-proof.md`

**Problem:** Mentions running `uv run pytest tests/browser/` but does not acknowledge the 24 existing test files or specify which are critical.

**Fix:** Create `docs/automate3-ui/artifacts/test-preservation-contract.md`:

**Must Pass Without Modification (sacred tests):**
- `test_browser_static_ui.py` — verifies static assets load
- `test_browser_control.py` — verifies basic controls respond
- `test_browser_interactions.py` — verifies core user interactions
- `test_project_lifecycle_contracts.py` — verifies new/open/save project
- `test_scoring_metrics_contracts.py` — verifies scoring and metrics
- `test_timing_waveform_contracts.py` — verifies waveform behavior
- `test_settings_e2e.py` — verifies settings persistence
- `test_merge_export_contracts.py` — verifies merge and export
- `test_workspace_flows.py` — verifies workspace routes
- `test_library_backend_contracts.py` — verifies library routes

**May Need DOM Updates if structure changes:**
- `test_browser_rail_layout.py` — if rail is hidden in Match/Library
- `test_browser_control_inventory_audit.py` — if control IDs change
- `test_browser_control_coverage_matrix.py` — if new controls are added
- `test_landing_page.py` — if landing DOM changes significantly

**New Tests Required:**
- View switching: landing → stage → match → library → landing
- Match grid: render, select, open stage, return
- Library: filter, select, detail, tag/note edit
- Export progress: stage export, batch export
- Empty/loaded state screenshots via headless browser

---

### 3.7 Missing Exact Error State Specifications

**Affected file:** `docs/automate3-ui/tracks/09-empty-loading-error-and-responsive-states.md`

**Problem:** Lists error states but does not specify the exact UX for each.

**Fix:** Expand with this table:

| State | Visual Treatment | Copy | Primary Action | Secondary Action |
|---|---|---|---|---|
| Route failure | Red banner in shell, persists until dismissed | "Unable to load {view}. {error detail}." | Retry | Go Home |
| No media in Stage | Centered empty state graphic + dark illustration placeholder | "Import a video to begin editing this stage." | Import Video | Open File |
| No match open | Centered empty state | "Create a match or open a recent one to get started." | New Match | Open Recent |
| Match with no stages | Inline hint inside match workspace | "This match has no stages yet. Add your first stage." | Add Stage | — |
| Empty library | Centered empty state | "No performance history yet. Complete a stage or match to see records here." | — | — |
| Missing proxy | Inline warning in detail panel | "Proxy not generated. Generate a proxy to preview this stage." | Generate Proxy | — |
| Stale proxy | Inline warning | "Proxy is out of date. Refresh to see the latest version." | Refresh Proxy | Dismiss |
| Failed export | Inline error + console log | "Export failed: {reason}. Check the log for details." | Retry | Dismiss |
| Unresolved reopen target | Disabled button with tooltip | "Cannot open: {reason}" | — | — |

---

## 4. Needs Clarification — Should Be Updated

### 4.1 Apply-From-First Logic Is Misleading

**Affected file:** `docs/automate3/04-match-video-edit-spec.md`

**Problem:** Describes a rich "preview changes before applying" flow with "affected stages, settings to apply, and override conflicts." The server implementation does none of this.

**Fix:** Add this backend gap note to the Match spec:

> **Backend Gap — Apply From First:**
> The current `/api/workspace/apply-from-first` and `/api/workspace/apply-from-first/preview` routes are metadata-only. They do not diff or copy actual project settings (output profiles, overlay visibility, export settings, etc.) from Stage 1's project to sibling stages. A complete implementation requires:
> 1. Diffing the actual `Project` state of Stage 1 against each sibling stage.
> 2. Generating a preview of concrete changes (e.g., "Stage 3 will inherit Video Shape: 16:9").
> 3. Detecting conflicts where a sibling has an explicit override.
> 4. Applying the changes to sibling stage projects and persisting them.
> **The UI must not claim this feature is complete until the backend supports it.**

---

### 4.2 Output Profile Render Is Under-Specified

**Affected file:** `docs/automate3/03-stage-video-edit-spec.md`

**Problem:** Says "render-plan preview and render result" but doesn't explain what a render plan contains.

**Fix:** Add:

> **Render Plan Content:**
> The render plan returned by `controller.output_profile_render(output_id)` is a dict containing:
> - `steps`: ordered list of pipeline steps (e.g., "trim dead time", "apply overlay", "encode H.264")
> - `estimated_duration_ms`: approximate render time based on source duration and preset
> - `output_path`: target file path
> - `dimensions`: `{width, height}`
> - `frame_rate`: target frame rate
> - `has_warnings`: boolean if settings conflict with source media
> The UI must display this as a read-only preview panel before the user confirms render.

---

### 4.3 Landing Recent Activity Data Source Mismatch

**Affected files:** `docs/automate3/02-end-to-end-workflow-spec.md`, `docs/automate3-ui/tracks/03-landing-page.md`

**Problem:** Workflow spec says Landing shows "recent activity with Stage, Match, and Library records." The `_handle_landing_recent` route scans `~/.splitshot/projects` and returns only `type: "stage"` entries.

**Fix:** Add to both files:

> **Current Limitation:** The `/api/landing/recent` route returns only stage project directories from `~/.splitshot/projects`. It does **not** return Match or Library records. The Landing Page UI must display what the route returns and must not fabricate Match/Library recent items. Future work may extend the route to aggregate library match records.

---

### 4.4 Flutter App Isolation Not Mentioned

**Affected file:** `docs/automate3/MASTER.md`, `docs/automate3-ui/MASTER.md`

**Problem:** `AGENTS.md` states: "Keep `flutter_app/` isolated to its own branch/worktree. Main must treat it as ignored branch-local work." Neither Automate3 MASTER file mentions this.

**Fix:** Add to both MASTER files under Non-Negotiables:

> 9. Do not modify `flutter_app/`. It is isolated to its own branch/worktree and must be treated as ignored branch-local work on `main`.

---

## 5. Proposed Changes in Priority Order

### Tier 1: Fix False Claims (blocks clean planning)
1. `docs/automate3/01-current-state-audit.md` — Remove false screenshot claims.
2. `docs/automate3-ui/artifacts/current-screenshot-audit.md` — Same.
3. `docs/automate3-ui/progress.md` — Remove artifact references; mark Phase 0 blocked on capture.
4. `docs/automate3/14-truth-audit-matrix.md` — Replace vague statuses with specific repo findings.

### Tier 2: Add Missing Technical Contracts (prevents ambiguity)
5. **New:** `docs/automate3-ui/artifacts/dom-restructure-plan.md` — Exact DOM mapping.
6. **New:** `docs/automate3-ui/artifacts/file-change-map.md` — Per-file change requirements.
7. **New:** `docs/automate3-ui/artifacts/visual-design-contract.md` — Color, spacing, typography tokens.
8. **New:** `docs/automate3-ui/artifacts/test-preservation-contract.md` — Sacred tests + new tests.
9. `docs/automate3/06-data-model-and-state-contract.md` — Add state integration appendix.
10. `docs/automate3-ui/execution-order.md` — Add phased migration strategy.

### Tier 3: Clarify Known Gaps (prevents backend/UI mismatch)
11. `docs/automate3/07-api-and-backend-contract.md` — Add "Routes With Known Backend Gaps" section.
12. `docs/automate3/04-match-video-edit-spec.md` — Add backend gap note for apply-from-first.
13. `docs/automate3/03-stage-video-edit-spec.md` — Clarify render plan content.
14. `docs/automate3-ui/tracks/09-empty-loading-error-and-responsive-states.md` — Add exact error state UX table.
15. `docs/automate3/02-end-to-end-workflow-spec.md` — Add landing recent limitation note.
16. `docs/automate3/MASTER.md` and `docs/automate3-ui/MASTER.md` — Add flutter_app isolation rule.

---

## 6. Final Assessment

| Criterion | Assessment | Notes |
|---|---|---|
| Product vision | ✅ Good | Four views, integrated but separate, Shotcut lessons adapted correctly |
| Naming contract | ✅ Good | Clear, binding, user-facing names are correct |
| Quality bar | ✅ Good | "No placeholder-complete claims" is the right stance |
| Current state audit | ⚠️ Partially false | Screenshot artifacts referenced but missing |
| API contract | ⚠️ Too thin | Lists routes but hides flawed implementations; no payload schemas |
| Technical architecture | ⚠️ Too thin | No DOM plan, no file map, no migration strategy |
| UI track specs | ⚠️ Too thin | Lists requirements but lacks DOM/CSS/error specifics |
| Proof discipline | ✅ Good | Non-vision agent rule is excellent |
| Test integration | ⚠️ Missing | Does not account for 24 existing browser test files |
| Execution order | ✅ Good | Logical, but needs migration detail added |

**Bottom line:** The Automate3 package is a correct **product brief** but an incomplete **build spec**. An implementation agent needs the Tier 1 fixes and Tier 2 new contracts before it can make consistent, test-preserving changes. Do not begin implementation until this review document is read, understood, and its proposed changes are applied.
