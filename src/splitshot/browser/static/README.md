# Browser Static Assets

<!-- Documentation reviewed: 2026-08-11 -->

This directory contains the browser-first SplitShot shell that talks to the local API.

## Module Layout

The frontend has been modularized into ES modules with clear boundaries:

| Directory | Purpose | Files |
|-----------|---------|-------|
| `lib/` | Backbone/shared runtime (event bus, state store, API client, layout, keys, activity, processing, shell-runtime, waveform-state, global-compat, utils) | 11 modules |
| `components/` | Reusable UI components (status-bar, video-player, waveform, overlay-canvas) | 4 modules |
| `panes/` | Pane modules for all 15 rail surfaces — each owns its behavior and rendering | 15 modules |
| `styles/` | Split CSS by responsibility (theme, layout, components, panes, widgets) | 5 files |
| `app.js` | Bootstrap entry point — imports all modules, wires dependencies, delegates to module factories | ESM \`<script type="module">\` |

## Key Files

| File | Role |
|------|------|
| [index.html](index.html) | Browser shell structure; defines pane order, control ids, and the module script tag |
| [app.js](app.js) | Bootstrap-only — 26 import statements, delegates to module factories, manages the legacy global compat bridge |
| [styles.css](styles.css) | `@import` loader that concatenates the 5 split CSS files |
| [lib/shell-runtime.js](lib/shell-runtime.js) | Central shell rendering and event coordination (render, wireEvents, renderControls) |
| [lib/global-compat.js](lib/global-compat.js) | Legacy page-global bridge installer (temporary — to be narrowed before PWA) |
| [lib/api.js](lib/api.js) | API coordination with stale-request tracking and draft preservation |
| [panes/pane-base.js](panes/pane-base.js) | Generic pane expand/collapse base class |
| [panes/*-pane.js](panes/) | Individual pane modules (scoring, settings, metrics, project, merge, export, review, shotml, overlay, markers, timing) |

## Shell Structure

`index.html` is organized into these major regions:

- the left rail with Project, Media, Compose, Trim, Score, Splits, Markers, Overlay, Review, Export, In / Out, Queue, Metrics, ShotML, and Settings tools
- the persistent top status bar that shows the selected video name or \`No Video Selected\` and keeps the shared layout lock in the upper-right corner
- the review grid with the stage preview, waveform, timing workbench, and inspector
- inspector panes for project metadata, stage media, composition, trimming, scoring, timing, markers, overlays, review text boxes, export settings, queue execution, metrics, ShotML, and settings
- the color picker and processing-log modals used by overlay, markers, review, Trim, and Queue controls

## Browser State Flow

The main loop is:

1. Fetch `/api/state` or post to an API route via `lib/api.js`.
2. `api.js` applies the payload to browser state via `applyRemoteState()`.
3. `app.js` delegates rendering to `lib/shell-runtime.js` which calls pane/component renderers.
4. User actions are mirrored into `/api/activity`.
5. Poll `/api/activity/poll` so export progress and log output can update in real time.

## Shell Behavior

- Layout sizing uses CSS variables such as `--app-height`, `--rail-width`, `--inspector-width`, and `--waveform-height`.
- The page shell remains bounded to the visible viewport at supported effective zoom levels. Scrolling belongs to the active inspector or expanded workbench instead of the document.
- Portrait and landscape media remain centered and fully visible with `object-fit: contain`; overlay coordinates are measured against the rendered video frame, not its surrounding stage.
- Waveform zoom, waveform offset, and active tool state persist in `localStorage`.
- Review and export overlays share the same repeatable text-box model, including imported summary boxes and manual notes. Review box editors are always expanded; the serialized `review_text_box_expansion` field remains readable for backward compatibility but does not control rendering.
- Overlay, Review, Compose, and Export presentation edits waterfall from the active stage to later stages until a later stage is edited directly. Review auto-summary values remain stage-specific, and Queue renders the same configured boxes, metrics, badges, and placement shown in preview.
- Shot-level score and penalty edits live in the Scoring pane; the Splits pane focuses on timing edits.
- The In / Out sidebar item opens the Intro / Outro pane, which stores project-managed boundary videos, persists independent audio/video fades, previews text boxes through the same overlay contract as stage exports, and offers selectable match-level result fields.
- Metrics begins with Match Metrics and a collapsed Stage Breakdown tree, with complete stage-specific cards, graphs, scoring context, and shot rows inside each branch. Expanded Metrics is one internally scrolling workspace with a sticky header and responsive graph columns. Dense competitor axes show rank numbers plus `You`, while focusable bars expose the full competitor name, rank, and value.
- Markers are separate from review text boxes and can be time-based, shot-linked, image-based, or motion-following, with a compact pane for browsing and a dedicated workbench for focused editing.
- Queue and multi-stage Trim processing use the green processing bar for aggregate per-video progress. Their shared live processing log is available from the pane that starts the work.
- Export profiles persist framing and ffmpeg controls. The Intro / Outro pane owns boundary media and overlays. Queue owns inclusion choices, execution, project-level fades, and output-folder reveal.
- Browser controls are normalized for WebKit and Safari-class browsers so native inputs remain usable in the cockpit layout.

## Editing Notes

- The browser shell depends directly on `browser/server.py` routes; update both sides when changing action names or payload contracts.
- After editing static assets, reload the running page before validating behavior so you are not testing a stale bundle.

## Rendering and persistence rules

- Ordinary value commits update existing controls in place whenever pane structure is unchanged.
- Structural actions rebuild only their owned component. Full synchronization is reserved for pane entry, project load, stage switch, and explicit reset.
- Pointer interactions defer server-driven rendering until the gesture commits or cancels; the active control remains connected throughout the gesture.
- Every complete-state API response is ordered against all other complete-state mutations, not only its route family. An older response cannot overwrite a newer interaction.
- Draft state protects active edits until the server confirms the same value. Successful server state remains authoritative without interrupting the active interaction.
- Stage defaults waterfall only into later stages that still inherit that field; directly customized stage values remain owned by that stage.
- When adding a new pane, create a `panes/<name>-pane.js` module, import it in `app.js`, create its HTML section in `index.html`, and register it in the global compat bridge if needed.

## Rendering and persistence rules

- Ordinary value commits update existing controls in place whenever pane structure is unchanged.
- Structural actions rebuild only their owned component. Full synchronization is reserved for pane entry, project load, stage switch, and explicit reset.
- Pointer interactions defer server-driven rendering until the gesture commits or cancels; the active control remains connected throughout the gesture.
- Every complete-state API response is ordered against all other complete-state mutations, not only its route family. An older response cannot overwrite a newer interaction.
- Draft state protects active edits until the server confirms the same value. Successful server state remains authoritative without interrupting the active interaction.
- Stage presentation defaults waterfall only into later stages that still inherit that field; directly customized stage values remain owned by that stage.
