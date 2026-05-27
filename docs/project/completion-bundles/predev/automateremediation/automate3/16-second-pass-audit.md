> **Note:** Historical audit. Not a current readiness gate.


# Second-Pass Pre-Implementation Review

> **Status:** All 12 gaps identified in this audit were resolved in the planning package by 2026-05-21. Core UI implementation is now ~80% complete. This document is retained as an audit trail.
>
> **Written:** 2026-05-21
> **Scope:** `docs/automate3/` and `docs/automate3-ui/`

---

## 1. Executive Summary

The first review identified **16 issues** across factually false claims, missing technical contracts, and needed clarifications. **The other agent addressed approximately 14 of 16.** Two material gaps remain, plus **4 new gaps** introduced by the update that were not caught in the first review. This document records what was fixed, what remains, and what is new.

---

## 2. What Was Fixed (Verified)

### Tier 1 — False Claims (All Fixed)

| # | Issue | Status | Evidence |
|---|---|---|---|
| 1 | Screenshot artifacts claimed to exist but missing | ✅ Fixed | `01-current-state-audit.md`, `current-screenshot-audit.md`, `progress.md` all now say "not guaranteed in repo truth / must be regenerated in Phase 0" |
| 2 | API contract hid stub implementations | ✅ Fixed | `07-api-and-backend-contract.md` now has "Routes With Known Backend Gaps" section listing 6 specific gaps with repo truth |
| 3 | Truth audit matrix vague | ✅ Fixed | `14-truth-audit-matrix.md` now lists specific controller methods, line numbers, and behaviors |

### Tier 2 — Missing Technical Contracts (All Fixed)

| # | Issue | Status | Evidence |
|---|---|---|---|
| 4 | No DOM restructure plan | ✅ Fixed | New `artifacts/dom-restructure-plan.md` with exact element-to-view mapping and target DOM skeleton |
| 5 | No per-file change map | ✅ Fixed | New `artifacts/file-change-map.md` with file/role/change table |
| 6 | No visual design tokens | ✅ Fixed | New `artifacts/visual-design-contract.md` with palette, spacing, typography, control tokens |
| 7 | No state integration plan | ✅ Fixed | `06-data-model-and-state-contract.md` has new "State Integration Rules" appendix |
| 8 | No migration strategy | ✅ Fixed | `execution-order.md` now has Phase 1a–1d (Wrap, Move, Hide, Retire) |
| 9 | No test preservation contract | ✅ Fixed | New `artifacts/test-preservation-contract.md` with sacred tests, DOM-update tests, and new tests |

### Tier 3 — Needed Clarifications (All Fixed)

| # | Issue | Status | Evidence |
|---|---|---|---|
| 10 | Apply-from-first backend gap undocumented | ✅ Fixed | `04-match-video-edit-spec.md` has "Backend gap" note with 4 required steps |
| 11 | Render plan under-specified | ✅ Fixed | `03-stage-video-edit-spec.md` has "Render Plan Target Contract" with exact payload fields |
| 12 | Landing recent data source mismatch | ✅ Fixed | `02-end-to-end-workflow-spec.md` line 16 notes route returns stage projects only; `spec.md` line 34 repeats it |
| 13 | flutter_app isolation unmentioned | ✅ Fixed | Both `MASTER.md` files now have Non-Negotiable #9 / Standing Rule #10 |
| 14 | No exact error state UX | ✅ Fixed | `tracks/09-empty-loading-error-and-responsive-states.md` now has full table |

### Cross-References (All Fixed)

| # | Issue | Status | Evidence |
|---|---|---|---|
| 15 | automate3-ui README doesn't list new artifacts | ✅ Fixed | `README.md` lines 20–29 now includes all 4 new artifacts |
| 16 | automate3-ui MASTER doesn't reference new artifacts | ✅ Fixed | `MASTER.md` Standing Rule #11 references all 4 new artifacts |
| 17 | UI subagent prompt doesn't reference new artifacts | ✅ Fixed | `07-subagent-orchestration-prompt.md` lines 9–12 now lists dom-restructure-plan, file-change-map, visual-design-contract, test-preservation-contract |

---

## 3. What Remains Missing or Needs Correction

### Gap A: `docs/automate3/12-subagent-orchestration-prompt.md` Still Missing New Artifacts

**Severity:** High — this is the primary orchestration prompt for backend-aware agents.

**Problem:** The `automate3` subagent prompt (not the `automate3-ui` one) still only lists 15 read-first items. It does **not** include `dom-restructure-plan.md`, `file-change-map.md`, `visual-design-contract.md`, or `test-preservation-contract.md`. An agent reading only this prompt would miss the critical new contracts.

**Fix:** Add items 16–19 referencing the 4 new artifacts, and item 20 for the pre-implementation review.

---

### Gap B: `docs/automate3/09-implementation-roadmap.md` Does Not Reference Phased Migration

**Severity:** High — this is the canonical roadmap.

**Problem:** Step 2 says "Split Architecture Into Real Views" as a single bullet. It does not mention the Wrap → Move → Hide → Retire migration strategy defined in `execution-order.md`. An agent might do a big-bang rewrite instead of the safe incremental approach.

**Fix:** Update Step 2 to reference the phased migration and the `execution-order.md` document.

---

### Gap C: `docs/automate3/08-technical-architecture.md` Still Has Flat File List

**Severity:** Medium — could cause inconsistent changes.

**Problem:** The architecture doc lists "Likely Files To Change" as a flat bulleted list. It does not reference `file-change-map.md` where the exact per-file changes are specified. An agent might read the architecture doc but miss the detailed file map.

**Fix:** Add a sentence after the file list: "For exact per-file changes, see `../automate3-ui/artifacts/file-change-map.md`."

---

### Gap D: `docs/automate3/README.md` Does Not Reference `15-pre-implementation-review.md`

**Severity:** Low — but the review doc contains valuable context.

**Problem:** The read order in `README.md` stops at `14-truth-audit-matrix.md`. It does not include the pre-implementation review, which explains why the plan was updated and what was found.

**Fix:** Add item 19 for `15-pre-implementation-review.md`.

---

### Gap E: `visual-design-contract.md` Proposes Colors That Conflict With Existing `theme.css`

**Severity:** High — this could cause an agent to break the existing visual identity.

**Problem:** The visual design contract proposes:
- Accent `#3b82f6` (blue)
- Background deepest `#0b0d10`
- Background deep `#111318`

But the existing `styles/theme.css` uses:
- `--accent: #ff7b22` (orange)
- `--bg: #050607` (deeper black)
- `--surface: #151719`

The existing app already has an orange accent used everywhere (active tool items, buttons, landing card hover, checkboxes, range thumbs). If an agent follows the visual design contract literally, it would change the app's entire color identity without being asked to do so. This is a recipe for visual inconsistency and broken tests.

**Fix:** Rewrite the visual design contract to reconcile with existing `theme.css`. Map existing CSS custom properties to the new token names. Add new tokens only where the existing theme is missing (e.g., view background differentiation, success/warning/error colors). Explicitly state: "Preserve existing `--accent: #ff7b22` and `--bg: #050607` unless a product decision to rebrand is made."

---

### Gap F: `dom-restructure-plan.md` Missing Shell Header Contents Specification

**Severity:** Medium — the shell header is a critical new element.

**Problem:** The plan shows `<header class="shell-header">` but does not list what goes inside it. An agent will guess, leading to inconsistent shell implementations.

**Fix:** Add a "Shell Header Contents" section listing: logo/home button, active view switcher (Stage/Match/Library), global context (project name, match name, stage name when applicable), return-to-match affordance, notification/status area, settings/help access.

---

### Gap G: `agent-rules.md` Does Not Reference New Artifacts

**Severity:** Medium — this is the rules file agents are supposed to read.

**Problem:** The "Before Editing" section says to read `MASTER.md` and `spec.md` and inspect current files. It does not mention the 4 new artifacts. An agent following only `agent-rules.md` might miss them.

**Fix:** Add the 4 artifact paths to the "Before Editing" checklist.

---

### Gap H: `spec.md` Does Not Cross-Reference Key Artifacts

**Severity:** Low — reduces discoverability.

**Problem:** `spec.md` says "professional dark visual treatment" but does not say "see `artifacts/visual-design-contract.md`". It says "empty state" but does not reference the exact UX table in `tracks/09-empty-loading-error-and-responsive-states.md`.

**Fix:** Add cross-references in the relevant sections.

---

### Gap I: `file-change-map.md` Missing Several CSS Files

**Severity:** Low — but an agent might forget them.

**Problem:** The file change map does not mention `styles/landing.css`, `styles/components.css`, or `styles/layout.css`. These files contain view-specific styles that will need updates during the restructure.

**Fix:** Add rows for these files.

---

### Gap J: `test-preservation-contract.md` Missing Many Existing Test Files

**Severity:** Low — but completeness matters.

**Problem:** The contract lists 10 sacred tests but there are 24 test files in `tests/browser/`. The remaining 14 are not mentioned, leaving ambiguity about their status.

**Fix:** Add a note acknowledging the remaining test files and stating that they must also pass unless their DOM assertions are intentionally updated as part of the migration.

---

### Gap K: `15-pre-implementation-review.md` Is Now Stale

**Severity:** Low — but the stale "do not begin" language is misleading.

**Problem:** Both copies of `15-pre-implementation-review.md` say "Do not begin implementation until the Tier 1 and Tier 2 items from this review are applied to the planning docs." Those items **have** been applied. The document is valuable as a historical audit trail, but its blocking language is now incorrect.

**Fix:** Add a top banner to both files: "This review's feedback was incorporated into the planning package on 2026-05-21. The package is now ready for implementation subject to Phase 0 execution."

---

## 4. New Issues Introduced by the Update

### New Issue 1: `spec.md` Landing Recent Copy Is Slightly Misleading

**Location:** `spec.md` line 34: "recent activity from `/api/landing/recent`; current backend returns stage project directories only, so do not fabricate Match/Library records until backend support exists"

**Problem:** The phrase "do not fabricate" is good, but the spec also says "three entry cards" and "quick starts: New Stage, New Match, Open File" on lines 33–35. An agent might still design the landing page with a "Recent Matches" section that is permanently empty, which is a poor UX. The spec should explicitly say: "The recent activity section displays only stage projects. Do not reserve UI space for Match or Library recent items until the backend route supports them."

**Fix:** Clarify the landing page spec to say the recent activity section should be titled "Recent Stages" (not "Recent Activity") until backend support exists.

---

## 5. Proposed Fixes in Priority Order

### Priority 1 (Material — Could Mislead Agent)
1. **`docs/automate3/12-subagent-orchestration-prompt.md`** — Add new artifacts to Read First list.
2. **`docs/automate3/09-implementation-roadmap.md`** — Reference phased migration (Wrap/Move/Hide/Retire).
3. **`docs/automate3-ui/artifacts/visual-design-contract.md`** — Reconcile with existing `theme.css` colors; do not change accent color without explicit request.

### Priority 2 (Important — Reduces Ambiguity)
4. **`docs/automate3/08-technical-architecture.md`** — Reference `file-change-map.md`.
5. **`docs/automate3-ui/artifacts/dom-restructure-plan.md`** — Add shell header contents specification.
6. **`docs/automate3-ui/agent-rules.md`** — Reference new artifacts in Before Editing section.
7. **`docs/automate3-ui/spec.md`** — Cross-reference visual-design-contract and error-state UX table.
8. **`docs/automate3/15-pre-implementation-review.md`** and `docs/automate3-ui/15-pre-implementation-review.md` — Add "feedback incorporated" banner.

### Priority 3 (Minor — Completeness)
9. **`docs/automate3/README.md`** — Add `15-pre-implementation-review.md` to read order.
10. **`docs/automate3-ui/artifacts/file-change-map.md`** — Add `landing.css`, `components.css`, `layout.css`.
11. **`docs/automate3-ui/artifacts/test-preservation-contract.md`** — Acknowledge remaining test files.
12. **`docs/automate3-ui/spec.md`** — Clarify landing recent section title should be "Recent Stages".

---

## 6. Final Assessment

| Package Aspect | Round 1 Score | Round 2 Score | Notes |
|---|---|---|---|
| Product vision | ✅ Good | ✅ Good | No change needed |
| Naming contract | ✅ Good | ✅ Good | No change needed |
| Quality bar | ✅ Good | ✅ Good | No change needed |
| Current state audit | ⚠️ False | ✅ Fixed | Screenshots now correctly noted as missing |
| API contract | ⚠️ Too thin | ✅ Fixed | Backend gaps explicitly documented |
| Truth audit matrix | ⚠️ Too vague | ✅ Fixed | Specific repo evidence recorded; updated for implementation state 2026-05-22 |
| Technical architecture | ⚠️ Too thin | ✅ Fixed | Now references file-change-map.md |
| DOM restructure plan | N/A | ✅ Good | New artifact, includes shell header contents |
| File change map | N/A | ✅ Fixed | Now includes landing.css, layout.css, components.css |
| Visual design contract | N/A | ✅ Fixed | Reconciled with existing theme.css; preserves --accent: #ff7b22 |
| State integration | ⚠️ Missing | ✅ Fixed | Appendix added to state contract |
| Migration strategy | ⚠️ Missing | ✅ Fixed | Phased strategy in execution-order |
| Test preservation | ⚠️ Missing | ✅ Fixed | Now acknowledges all existing test files |
| Error state UX | ⚠️ Missing | ✅ Fixed | Exact table added |
| Apply-from-first gap | ⚠️ Missing | ✅ Fixed | Backend gap documented |
| Render plan contract | ⚠️ Missing | ✅ Fixed | Payload fields specified |
| Landing recent limit | ⚠️ Missing | ✅ Fixed | Noted in workflow spec and UI spec; "Recent Stages" title clarified |
| flutter_app isolation | ⚠️ Missing | ✅ Fixed | Added to both MASTER files |
| Orchestration prompt cross-ref | ⚠️ Missing | ✅ Fixed | Both automate3 and automate3-ui prompts now reference new artifacts |
| Implementation roadmap | N/A | ✅ Fixed | Now references phased migration |
| Pre-implementation review stale | N/A | ✅ Fixed | "Feedback incorporated" banner added to both copies |

**Bottom line:** All 12 gaps (A-K + New Issue 1) were resolved in the planning package on 2026-05-21. The package was used for implementation and core UI work is now ~80% complete. See `progress.md` for current status.
