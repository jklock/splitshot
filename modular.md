# Modular Architecture Plan — SplitShot Browser UI

---

## 1. Current State: The Monolith

The frontend is a single 13,142-line vanilla JS file (`browser/static/app.js`) loaded via
a classic `<script>` tag with zero modularity. There are:

- **0** `import`/`export` statements
- **0** class definitions
- **0** module boundaries
- **~100+** global mutable variables shared across all panes
- **~200+** flat functions calling each other by name
- **1** monolithic `render()` that re-renders every pane on every state change
- **1** monolithic `wireEvents()` (600 lines) that wires every control in every pane

### How it got here

The app grew feature by feature, each new pane adding more global vars, more functions,
and more entries in `render()` and `wireEvents()`. The architecture that was fine at
2,000 lines became unmanageable at 13,000. There was never a refactor step to carve
out module boundaries.

### Symptoms

- Changing ShotML threshold re-renders the overlay, waveform, and timing tables
- `selectedShotId` is read/written by 8 different features across all panes
- `syncLocalProjectUiState()` mixes layout, waveform, timing, scoring, and popup state into one payload
- Adding a new control means editing the HTML, then finding the right spot in `wireEvents()`,
  then threading a new global variable through `readPayload()` → `scheduleApply()` → `autoApply()`
  → server endpoint → `applyRemoteState()` → `render()` path
- No way to test any pane in isolation — the entire state object must be present

---

## 2. Target Architecture: Pane Modules + Shared Backbone

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         SHARED BACKBONE                                 │
│                                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  │
│  │  Event Bus   │  │   API Kit    │  │  App Store   │  │ Layout Mgr │  │
│  │  (pub/sub)   │  │  (fetch +    │  │  (reactive   │  │ (rail,     │  │
│  │              │  │   transform) │  │   state)     │  │  resize)   │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └────────────┘  │
│                                                                         │
│  ┌──────────────┐  ┌──────────────┐                                    │
│  │   Utils      │  │  Keybindings │                                    │
│  │  ($, debounce│  │  (global     │                                    │
│  │   format,    │  │   keyboard)  │                                    │
│  │   colors)    │  └──────────────┘                                    │
│  └──────────────┘                                                      │
└─────────────────────────────────────────────────────────────────────────┘
         ▲              ▲              ▲              ▲              ▲
         │              │              │              │              │
         │      ┌───────┘              │              └───────┐      │
         │      │                      │                      │      │
┌────────┴──────┴──┐  ┌───────────┐  ┌┴──────────────┐  ┌────┴──────┴───┐
│   PANE MODULES   │  │  WIDGETS  │  │  VIDEO/WAVE   │  │  PERSISTENCE  │
│                  │  │           │  │  CANVAS       │  │               │
│  project-pane.js │  │color-picker│  │video-player.js│  │ui-state-sync  │
│  scoring-pane.js │  │modal.js   │  │waveform.js    │  │autosave.js    │
│  timing-pane.js  │  │badge.js   │  │overlay-canvas │  │activity.js    │
│  overlay-pane.js │  │           │  │renderer.js    │  │               │
│  markers-pane.js │  │           │  │               │  │               │
│  merge-pane.js   │  │           │  │               │  │               │
│  review-pane.js  │  │           │  │               │  │               │
│  export-pane.js  │  │           │  │               │  │               │
│  metrics-pane.js │  │           │  │               │  │               │
│  shotml-pane.js  │  │           │  │               │  │               │
│  settings-pane.js│  │           │  │               │  │               │
└──────────────────┘  └───────────┘  └───────────────┘  └───────────────┘
```

### Core principle: each pane owns its own slice of state, its own DOM, and its own lifecycle

A pane module is a plain JS object (or class) with:

```javascript
// Each pane module exports:
{
  id: "scoring",                  // matches data-tool-pane
  label: "Score",

  // State (pane-owned; no other module reads/writes these)
  state: {
    enabled: false,
    preset: "uspsa",
    editSet: new Set(),
    columnWidths: {},
  },

  // Lifecycle
  init(backbone) { /* register event listeners, wire DOM */ },
  destroy() { /* tear down */ },

  // Rendering
  render(stateSnapshot) { /* update own DOM only */ },
  onActivate() { /* pane was shown */ },
  onDeactivate() { /* pane was hidden */ },
}
```

---

## 3. The Shared Backbone (in detail)

### 3.1 Event Bus (`lib/event-bus.js`)

The only way panes communicate. No direct function calls between panes.

```javascript
// publish/subscribe with typed events
const bus = createEventBus();

bus.on("shot:selected", (shotId) => { ... });
bus.emit("shot:selected", "abc123");
bus.off("shot:selected", handler);

// Built-in event types:
//   state:changed         - any state update (payload: { path, value, source })
//   shot:selected         - shot selection changed (payload: shotId)
//   tool:activated        - pane switch (payload: toolId)
//   project:loaded        - project loaded/unloaded
//   api:response          - server returned data (payload: { path, data })
//   render:requested      - pane should re-render (payload: toolId?)
//   layout:resized        - rail/inspector/waveform resized
//   processing:start/end  - processing bar lifecycle
//   overlay:updated       - overlay needs redraw
```

### 3.2 App Store (`lib/store.js`)

A simple reactive store, not a full Redux. The server is the source of truth;
the store caches the last known full state and notifies subscribers of changes.

```javascript
const store = createStore();

// All panes subscribe to their slice
store.subscribe("project.analysis.shots", (shots) => { /* re-render */ });

// After API response, the API kit writes to the store
store.set("project.analysis.shots", newShots);  // triggers subscribers
```

Key difference from current `state` global: panes subscribe to **only their slice**,
so rendering is scoped. The `render()` function no longer calls every sub-renderer.

### 3.3 API Kit (`lib/api.js`)

Wraps fetch/response handling. Unlike the current `callApi()` which returns full state
and triggers a full re-render, the new API kit:

```javascript
const api = createApi();

// Returns parsed response data only (not full state)
const result = await api.post("/api/scoring", payload);

// Or use the reactive version which also updates the store:
await api.postAndSync("/api/scoring", payload, { scope: "scoring" });
// This posts, gets full state back, extracts the scoring slice,
// and only triggers subscribers of "scoring" paths.
```

### 3.4 Layout Manager (`lib/layout.js`)

Manages the rail, inspector, waveform, and workbench layout. Currently this is
a mix of global variables (`layoutSizes`, `railCollapsed`, `layoutLocked`) and
random DOM manipulation scattered throughout `render()`. Centralizing it means:

```javascript
const layout = createLayoutManager();

layout.getSizes();                 // { railWidth, inspectorWidth, waveformHeight }
layout.setSize("inspectorWidth", 500);
layout.subscribe((sizes) => { /* reposition canvas, resize video */ });
```

### 3.5 Keybindings (`lib/keys.js`)

Centralized keyboard handler instead of the current single `keydown` listener
at the bottom of `wireEvents()`:

```javascript
const keys = createKeybindings();

keys.register("Escape", () => { closeColorPicker(); closeExportLog(); });
keys.register("n", { ctrl: true }, () => { /* new project */ });
// Panes register their own keys on activate, unregister on deactivate:
pane.onActivate = () => keys.register("Delete", removeSelectedShot);
pane.onDeactivate = () => keys.unregister("Delete");
```

### 3.6 Utilities (`lib/utils.js`)

- `$(id)` — `document.getElementById` shorthand (keep as-is, but in a module)
- `debounce(fn, ms)` — keep as-is
- `formatTime(ms)` — currently duplicated in multiple places
- `formatDuration(ms)` — same
- `clamp(value, min, max)` — same

---

## 4. Pane Module Breakdown

### 4.1 Each pane module file

Named like `src/splitshot/browser/static/panes/<id>-pane.js`.

**Structure:**

```javascript
// panes/scoring-pane.js
import { createPane } from "../lib/pane-base.js";

export default createPane({
  id: "scoring",
  label: "Score",

  // DOM selectors within this pane's section
  elements: {
    enabled: "#scoring-enabled",
    preset: "#scoring-preset",
    table: "#scoring-table",
    result: "#scoring-result",
    // ...
  },

  // Initial state
  defaultState() {
    return {
      enabled: false,
      preset: "uspsa",
      editSet: new Set(),
      columnWidths: {},
    };
  },

  // Called once on startup
  init({ bus, store, api, elements }) {
    elements.enabled.addEventListener("change", () => {
      api.postAndSync("/api/scoring", { enabled: elements.enabled.checked }, { scope: "scoring" });
    });
    // ... more event wiring
  },

  // Called on every relevant state change
  render(scoringState) {
    // Only touches DOM elements in this pane
    elements.enabled.checked = scoringState.enabled;
    // ... build table rows, update result display
  },

  // Called when user switches to this pane
  onActivate() {
    // Focus first input, start polling if needed
  },

  // Called when user leaves this pane
  onDeactivate() {
    // Commit any pending drafts, stop timers
  },
});
```

### 4.2 What becomes of the current global variables

| Current Global | New Home |
|---|---|
| `state` | `store` in `lib/store.js` |
| `selectedShotId` | `store.get("ui.selectedShotId")` — event `shot:selected` |
| `activeTool` | `store.get("ui.activeTool")` — layout manager |
| `waveformZoomX`, `waveformOffsetMs` | `lib/waveform-state.js` (shared between waveform canvas and timing pane) |
| `waveformShotAmplitudeById` | `lib/waveform-state.js` |
| `overlayVisibilityPosition` etc. | `panes/overlay-pane.js` state |
| `popupFilterMode` etc. | `panes/markers-pane.js` state |
| `timingRowEdits`, `scoringRowEdits` | respective pane's state |
| `layoutSizes`, `railCollapsed`, `layoutLocked` | `lib/layout.js` |
| `busyCount`, `processing*` | `lib/processing.js` |
| `activityQueue`, `activityPollTimer` | `lib/activity.js` |
| `exportDraft` | `panes/export-pane.js` state |
| `projectDetailsDraft` | `panes/project-pane.js` state |
| `popupAutoTraceBubbleId` etc. | `panes/markers-pane.js` state |
| `draggingShotId`, `waveformPanDrag` etc. | `lib/waveform-state.js` |
| `overlayFrame`, `interactionPreviewFrame` | `lib/overlay-canvas.js` |

### 4.3 What happens to the monolithic functions

| Current Function | New Home |
|---|---|
| `render()` (line 11,506) | **Deleted.** Each pane renders itself via `store.subscribe()`. |
| `renderHeader()` | `panes/project-pane.js` (it's in the review-stack, not a pane — extracted to `components/status-bar.js`) |
| `renderStats()` | `components/status-bar.js` |
| `renderVideo()` | `components/video-player.js` |
| `renderWaveform()` | `components/waveform.js` |
| `renderTimingTables()` | **Deleted.** Timing table is rendered by `panes/timing-pane.js` |
| `renderControls()` | **Deleted.** Each pane renders its own controls |
| `renderLiveOverlay()` | `components/overlay-canvas.js` |
| `setActiveTool()` | `lib/layout.js` (emits `tool:activated` event) |
| `wireEvents()` (line 12,536) | **Deleted.** Each pane wires its own events in `init()` |
| `callApi()` / `api()` | `lib/api.js` |
| `applyRemoteState()` | **Deleted.** Store handles this via `api.postAndSync()` |
| `readProjectUiStatePayload()` | **Deleted.** Each pane persists its own slice of UI state |
| `scheduleProjectUiStateApply()` | **Deleted.** Replaced by per-pane persistence |
| `syncLocalProjectUiState()` | **Deleted.** |

### 4.4 Render optimization: scoped vs full re-render

**Current behavior:**
```
User clicks checkbox in overlay pane
  → callApi("/api/overlay", {show: true})
    → full server state response
      → applyRemoteState() overwrites entire state
        → render() calls ALL sub-renderers
```

**Target behavior:**
```
User clicks checkbox in overlay pane
  → api.postAndSync("/api/overlay", {show: true}, {scope: "overlay"})
    → full server state response
      → store.set("overlay", extractSlice(response, "overlay"))
        → only overlay-pane subscribers fire
          → panes/overlay-pane.js render() runs (touches only overlay DOM)
```

But some panes still need to react to each other:
- Changing ShotML threshold may change shot positions → timing pane needs to update
- Scoring a shot may change the overlay badge → overlay needs to update

These cross-pane updates happen via the event bus, not via monolithic re-render:

```
User clicks "Re-run ShotML" in shotml pane
  → api.postAndSync("/api/analysis/shotml-settings", ...)
    → shotml-pane renders its controls
    → store detects shots changed → emits "shot:updated"
      → timing-pane subscriber re-reads shots from store, re-renders table
      → overlay-canvas subscriber re-draws badges
      → waveform subscriber re-draws markers
```

---

## 5. Specific Coupling Issues to Untangle

### 5.1 `selectedShotId` — the central nexus

Currently written by waveform, timing table, scoring table, popup editor, and keyboard handler.
Read by 8+ features.

**Fix:** Move to `store.set("ui.selectedShotId", id)` + emit `shot:selected`. Each reader
subscribes to the `shot:selected` event or to `store.watch("ui.selectedShotId")`.

### 5.2 Review visibility toggles affecting overlay

Review pane has checkboxes (`show-markers`, `show-pip`, etc.) that control what the overlay
canvas draws. Currently this is:

1. Review pane checkbox change → `syncLocalProjectUiState()` → `scheduleProjectUiStateApply()`
   → POST → full state → `render()` → `renderLiveOverlay()`

**Fix:** Review pane emits `bus.emit("overlay:visibility", { markers: true, pip: false })`.
Overlay canvas subscribes to this event and redraws only the overlay layer (no re-render of
panes, no server round-trip for the toggle itself).

### 5.3 The composite `/api/project/ui-state` endpoint

Currently saves waveform zoom, active tool, expanded states, review toggles, column widths,
edit sets, and section expansions all in one POST. This means changing any one thing sends
everything.

**Fix:** Each pane manages its own ephemeral state in `localStorage` (as some already do) or
has its own tiny server endpoint. The only things that need server persistence are:
- `selected_shot_id` (so it survives page reload)
- `active_tool` (same)
- Maybe waveform zoom/offset (for session continuity)

Everything else (column widths, expanded sections, edit sets) is client-only or restored
from the server state snapshot on load.

### 5.4 Shared scroll container

All panes share the same `.inspector` scroll container. When the user scrolls down in the
timing pane (which has a long table) and switches to the merge pane, the merge pane inherits
the scroll position.

**Fix:** Each pane gets its own scroll container (or the scroll position is saved/restored
on pane switch). The simplest approach: switch `.inspector` from one scroll container to
per-pane scrollable divs, i.e. each `<section data-tool-pane>` becomes `overflow-y: auto`
and the parent `.inspector` becomes `overflow: hidden`.

### 5.5 Color picker and modal as shared widgets

The color picker and export log modal are currently global widgets that any pane can invoke.
They work across pane boundaries. These become shared widget modules in `widgets/` that
panes import and use:

```javascript
// In overlay-pane.js init():
import { openColorPicker } from "../widgets/color-picker.js";

elements.badgeColor.addEventListener("click", () => {
  openColorPicker({
    initialColor: "#1D4ED8",
    onCommit: (color) => api.postAndSync("/api/overlay", { badgeColor: color }, { scope: "overlay" }),
  });
});
```

---

## 6. File Organization

### Current:
```
browser/static/
├── index.html          (1,200 lines — HTML shell)
├── app.js              (13,142 lines — everything)
├── styles.css          (4,066 lines — everything)
├── logo.png
└── githublogo.png
```

### Target:
```
browser/static/
├── index.html                  (300 lines — slim shell, just loads modules)
│
├── lib/                        # Shared backbone
│   ├── event-bus.js            (~80 lines)
│   ├── store.js                (~100 lines)
│   ├── api.js                  (~120 lines — fetch, auth, transform)
│   ├── layout.js               (~150 lines — rail, inspector, waveform sizing)
│   ├── keys.js                 (~80 lines — keyboard shortcuts)
│   ├── utils.js                (~100 lines — $, debounce, clamp, format)
│   ├── processing.js           (~60 lines — processing bar)
│   └── activity.js             (~80 lines — telemetry queue)
│
├── components/                 # Shared visual components (not pane-specific)
│   ├── status-bar.js           (~80 lines — current file, status text)
│   ├── video-player.js         (~200 lines — primary/secondary video)
│   ├── waveform.js             (~800 lines — canvas rendering, interaction)
│   ├── overlay-canvas.js       (~500 lines — live overlay rendering)
│   └── data-table.js           (~150 lines — reusable table rendering)
│
├── widgets/                    # Shared modal widgets
│   ├── color-picker.js         (~200 lines)
│   ├── export-log-modal.js     (~80 lines)
│   └── modal.js                (~40 lines — modal shell)
│
├── panes/                      # One file per left-hand pane
│   ├── project-pane.js         (~200 lines)
│   ├── scoring-pane.js         (~300 lines)
│   ├── timing-pane.js          (~400 lines)
│   ├── overlay-pane.js         (~500 lines)
│   ├── markers-pane.js         (~600 lines)
│   ├── merge-pane.js           (~200 lines)
│   ├── review-pane.js          (~250 lines)
│   ├── export-pane.js          (~400 lines)
│   ├── metrics-pane.js         (~250 lines)
│   ├── shotml-pane.js          (~500 lines)
│   ├── settings-pane.js        (~600 lines)
│   └── pane-base.js            (~30 lines — createPane() factory)
│
├── app.js                      (~200 lines — bootstrap: init backbone, init panes)
│
├── styles/                     # Split CSS (instead of one 4k-line file)
│   ├── reset.css               (~50 lines)
│   ├── layout.css              (~400 lines — grid, shell, rail, inspector)
│   ├── panes.css              (~600 lines — all pane-specific styles)
│   ├── components.css          (~800 lines — video, waveform, overlay)
│   ├── widgets.css             (~300 lines — modals, color picker)
│   └── theme.css               (~100 lines — vars, colors, typography)
│
├── logo.png
└── githublogo.png
```

---

## 7. Migration Strategy

This is a significant refactor. Do NOT attempt in one pass.
Recommended order:

### Phase 1: Extract the backbone (safe, no behavioral change)

1. Create `lib/` directory with `event-bus.js`, `store.js`, `api.js`, `utils.js`,
   `layout.js`, `keys.js`, `processing.js`, `activity.js`
2. Each is extracted from existing code in `app.js` with zero behavioral change
3. Switch `index.html` to `<script type="module" src="app.js">` and load backbone modules
4. Keep the old global functions as wrappers that delegate to the new backbone
5. **Result:** backbone exists and is used, but old code still works unchanged

**Estimated effort:** 2–3 days
**Risk:** Low (pure extraction, no behavioral change)

### Phase 2: Extract components (medium risk)

1. Extract `status-bar.js`, `video-player.js`, `waveform.js`, `overlay-canvas.js`,
   `data-table.js`
2. These are also purely extracted — `render()` still calls them, but they're now in
   their own files with well-defined inputs (state snapshot) and outputs (DOM updates)
3. **Result:** key rendering functions are modular, but still called from `render()`

**Estimated effort:** 3–4 days
**Risk:** Medium (waveform has complex interaction state; careful not to break drag behavior)

### Phase 3: Extract one pane as a pilot (highest risk — proves the pattern)

1. Pick the **scoring pane** — it has the fewest cross-pane dependencies
2. Create `panes/scoring-pane.js` with its own state, render, event wiring
3. Remove its wiring from `wireEvents()` and its rendering from `renderControls()`
4. Verify: scoring still works, all other panes still work
5. Document issues found and adjust the pane base pattern
6. **Result:** proven pattern for all other panes

**Estimated effort:** 2–3 days
**Risk:** High (first one is always hardest; expect to iterate on the pattern)

### Phase 4: Extract remaining panes (lower risk, pattern established)

1. Extract one pane per day in order of increasing cross-pane coupling:
   - `settings-pane.js` (self-contained)
   - `merge-pane.js` (few dependencies)
   - `metrics-pane.js` (read-only, simplest)
   - `project-pane.js` (file I/O, few cross-dependencies)
   - `export-pane.js` (self-contained)
   - `review-pane.js` (only wired to overlay visibility)
   - `shotml-pane.js` (complex form, but self-contained state)
   - `overlay-pane.js` (many controls, but no table rendering)
   - `markers-pane.js` (complex: popup editor, template management)
   - `timing-pane.js` (most complex: table, drag, keyboard navigation)

2. After each pane, verify: `wireEvents()` is smaller, `render()` does less
3. **Result:** monolith is dismantled

**Estimated effort:** 10–14 days
**Risk:** Medium (each pane extraction may reveal hidden coupling)

### Phase 5: Delete the monolith

1. Once all panes are extracted, delete `render()`, `wireEvents()`, `read*Payload()`,
   `schedule*Apply()`, `autoApply*()` from the old code
2. The leftover shared global variables get their final migration to the store
3. `app.js` becomes ~200 lines: init backbone, init panes, init components
4. **Result:** fully modular architecture

**Estimated effort:** 2 days
**Risk:** Medium (must verify nothing was missed)

### Phase 6: Split CSS

1. Extract styles from the single `styles.css` into the `styles/` directory
2. Each pane's styles go in `panes.css` with a section comment
3. **Result:** CSS is navigable

**Estimated effort:** 1 day
**Risk:** Low

---

## 8. Total Effort Estimate

| Phase | Description | Days | Risk |
|---|---|---|---|
| 1 | Extract backbone | 2–3 | Low |
| 2 | Extract components | 3–4 | Medium |
| 3 | Pilot pane (scoring) | 2–3 | High |
| 4 | Remaining 10 panes | 10–14 | Medium |
| 5 | Delete monolith | 2 | Medium |
| 6 | Split CSS | 1 | Low |
| **Total** | | **20–27 working days** | |

---

## 9. How Far Off We Are

**Short answer: very far.** The entire JS application would need to be rewritten in-place.
This is not a "tweak the import system" situation — there is no import system, no module
pattern, and the code has grown organically with no abstraction boundaries.

**What we already have going for us:**

| Asset | Status |
|---|---|
| HTML structure | **Good** — `data-tool-pane` attributes cleanly identify each pane's DOM |
| CSS class patterns | **Good** — consistent `.control-grid`, `.button-grid`, `.section-header` patterns |
| Server API endpoints | **Good** — 42 focused endpoints, each returns full state (easy to scope later) |
| `browser/state.py` | **Good** — single function builds the full state dict; easy to add `extract_slice()` helpers |

**What we need to build from scratch:**

| Component | Status |
|---|---|
| Module system (ES modules) | **Non-existent** — `index.html` uses `<script>` not `<script type="module">` |
| Event bus | **Zero lines exist** — must be written |
| Reactive store | **Zero lines exist** — must be written |
| API kit with scoped sync | **Zero lines exist** — must be written |
| Layout manager | **Zero lines exist** — currently spread across global vars |
| Pane base factory | **Zero lines exist** — must be designed and written |
| Each pane module | **Zero lines exist** — every pane's logic must be extracted |
| Component modules | **Zero lines exist** — waveform, overlay, video player must be extracted |
| Widget modules | **Zero lines exist** — color picker, modal must be extracted |

**Verdict:** The refactor is essentially rebuilding the frontend on a new architecture,
piece by piece, keeping the existing code running until each piece is replaced. It's
a 4–6 week full-time project for one developer, done carefully with testing after
each phase.

---

## 10. Risk Mitigation

### 10.1 Testing during migration

- After Phase 1 (backbone), existing tests should still pass because no behavior changed
- After Phase 3 (pilot pane), write a focused Playwright test for the scoring pane
- After each subsequent pane extraction, run the full browser test suite
- The `tests/browser/` suite (213 test functions) is the safety net

### 10.2 Keeping the app shippable during the refactor

- Never have a broken commit. Each PR should extract one piece and leave the old wiring
  in place (the new module and the old function coexist; the new module is just not
  connected yet, or the old function delegates to the new module)
- The "switchover" for each pane is a single PR that changes what `render()` calls

### 10.3 Avoiding scope creep

- Do NOT redesign the state shape or API protocol during the refactor — keep the same
  server contract, just change the client-side organization
- Do NOT add features during the refactor
- Do NOT optimize performance yet — the modular architecture is the foundation for
  future perf work (virtual scrolling, canvas diffing, etc.), but that's Phase 7+
