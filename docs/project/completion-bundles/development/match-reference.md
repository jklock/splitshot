# Match Reference Map

This is the developer-facing reference for the Match workspace.

Use this file when you need to answer any of these questions quickly:

- Which visible Match control owns this behavior?
- Which route does it call?
- Which controller method mutates the state?
- What data actually changes?
- Where is that data persisted?
- Which tests prove the control or feature?

For the user-facing explanation of Match, see [`../../../../docs/userfacing/panes/match.md`](../../../../docs/userfacing/panes/match.md).

## How to read this doc

- The **reference sheet** is organized by visible Match section and focuses on buttons plus stateful controls.
- The **architecture map** traces feature flows from browser UI to persistence and output files.
- The **code map** calls out the main files and symbols that own Match behavior.
- The **test crosswalk** maps buttons and features to the tests that currently prove them.

A few Match controls are purely browser-local. Those rows use `—` for route and controller ownership and point to local storage or in-memory UI state instead.

## Match family proof-taxonomy summary

This summary stays family-level. Use the literal reference sheet when one Match family contains both runtime-only setup controls and proof-bearing persisted or output actions.

| Match family | Proof-taxonomy summary | Honesty caveat |
| --- | --- | --- |
| Shell navigation and selected-stage framing | Mostly `LOCAL_PERSISTED_UI` + `RUNTIME_EPHEMERAL`. | Pinned lower-pane truth and shell guardrails matter, but section toggles or selection alone do not close meaningful claims. |
| Workspace lifecycle / stage membership / defaults / overrides / apply-from-first | `PERSISTED_MODEL`. | Meaningful closure comes from saved workspace/stage/profile truth, not just a visible card, banner, or preview. |
| Recap | Mixed `RUNTIME_EPHEMERAL` + `OUTPUT_ARTIFACT`. | Stage selection/order/options are runtime-only until `Render Recap` produces `recap.mp4`. |
| Composite clip editing | Mixed `PERSISTED_MODEL` + `OUTPUT_ARTIFACT`. | Clip/source/cut/audio state persists, but `Plan` inspection alone is lighter than applied overrides or exported composite output. |
| Batch export | Mixed `RUNTIME_EPHEMERAL` + `OUTPUT_ARTIFACT`. | Queue checkboxes and recipe choice alone do not close the lane; exported files do. |
| Match settings | `LOCAL_PERSISTED_UI`. | These settings prove only local Match UI behavior, not workspace or Stage domain truth. |

## Literal reference sheet

### Shell and workspace lifecycle

| Section | Button / control | DOM id / selector | Browser owner | Route | Server handler | Controller method | Data changed | Persistence type |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Shell | `Stages` | `[data-workspace-target="match-section-stages"]` | `app.js` → `setWorkspaceSection("match", ...)` | — | — | — | active Match section | browser `localStorage` (`splitshot.match.section`) |
| Shell | `Defaults` | `[data-workspace-target="match-section-defaults"]` | `app.js` → `setWorkspaceSection("match", ...)` | — | — | — | active Match section | browser `localStorage` |
| Shell | `Overrides` | `[data-workspace-target="match-section-overrides"]` | `app.js` → `setWorkspaceSection("match", ...)` | — | — | — | active Match section | browser `localStorage` |
| Shell | `Recap` | `[data-workspace-target="match-section-recap"]` | `app.js` → `setWorkspaceSection("match", ...)` | — | — | — | active Match section | browser `localStorage` |
| Shell | `Composite` | `[data-workspace-target="match-section-composite"]` | `app.js` → `setWorkspaceSection("match", ...)` | — | — | — | active Match section | browser `localStorage` |
| Shell | `Export` | `[data-workspace-target="match-section-export"]` | `app.js` → `setWorkspaceSection("match", ...)` | — | — | — | active Match section | browser `localStorage` |
| Shell | `Home` | `#match-go-home` | `app.js` | — | — | — | active surface | browser runtime only |
| Shell | Match settings gear | `#match-open-settings` | `app.js` | — | — | — | active Match section | browser `localStorage` |
| Shell | rail collapse | `#match-toggle-rail` | `app.js` → `setWorkspaceRailCollapsed("match", ...)` | — | — | — | rail collapsed state | browser `localStorage` (`splitshot.match.railCollapsed`) |
| Empty state | `New Match` | `#workspace-new-empty` | `app.js` | `POST /api/workspace/new` | `browser.server._new_workspace` | `ProjectController.new_workspace` | new `MatchWorkspace`, Match scope flags, seeded defaults | in-memory until saved |
| Lifecycle | `New Workspace` | `#workspace-new` | `app.js` | `POST /api/workspace/new` | `browser.server._new_workspace` | `ProjectController.new_workspace` | new `MatchWorkspace`, `workspace_path=None`, `editor_scope="multi"` | in-memory until saved |
| Lifecycle | `Open Workspace` | `#workspace-open` | `app.js` → `openWorkspaceWithPicker()` | `POST /api/dialog/path`, `POST /api/workspace/open` | `browser.server._choose_dialog_path`, `browser.server._open_workspace` | `ProjectController.open_workspace` | current workspace, stage profiles, Match state | loads saved workspace bundle |
| Lifecycle | `Save Workspace` | `#workspace-save` | `app.js` → `saveWorkspaceFromUi()` | `POST /api/dialog/path`, `POST /api/workspace/save` | `browser.server._choose_dialog_path`, `browser.server._save_workspace` | `ProjectController.save_workspace` | workspace metadata, per-stage profiles, library match record | workspace bundle + library record |

### Stage list, selected stage, and workflow shortcuts

| Section | Button / control | DOM id / selector | Browser owner | Route | Server handler | Controller method | Data changed | Persistence type |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Stage list | `Stage name` | `#workspace-stage-name` | `index.html` + `app.js` add-stage handler | — | — | — | pending text only | browser input state |
| Stage list | `Add Stage` | `#workspace-stage-add` | `app.js` | `POST /api/workspace/stage/add` | `browser.server._workspace_add_stage` | `ProjectController.workspace_add_stage` | `MatchWorkspace.stage_entries`, `stage_order`, `updated_at` | workspace bundle |
| Stage card | stage tile click | `.match-stage-card` | `match-view.js` → `renderWorkspaceStages()` | — | — | — | selected stage id for Match UI | browser runtime only |
| Stage card | `Open` | `.match-stage-action` (`Open`) | `match-view.js` | `POST /api/workspace/stage/open` | `browser.server._workspace_open_stage` | `ProjectController.workspace_open_stage` | opened stage context, `_return_to_workspace_available`, active stage id | runtime + stage project open |
| Stage card | `Remove` | `.match-stage-action` (`Remove`) | `match-view.js` | `POST /api/workspace/stage/remove` | `browser.server._workspace_remove_stage` | `ProjectController.workspace_remove_stage` | `stage_entries`, `stage_order`, `updated_at` | workspace bundle |
| Stage card | `Reset` | `.match-stage-action` (`Reset`) | `match-view.js` | `POST /api/workspace/stage/override/reset` | `browser.server._workspace_reset_stage_override` | `ProjectController.workspace_reset_stage_override` | `StageEntry.override_values`, stage status | workspace bundle |
| Selected Stage | `Open In Stage` | `[data-selected-stage-action="open"]` | `match-view.js` | `POST /api/workspace/stage/open` | `browser.server._workspace_open_stage` | `ProjectController.workspace_open_stage` | same as stage-card `Open` | runtime + stage project open |
| Selected Stage | `Remove Stage` | `[data-selected-stage-action="remove"]` | `match-view.js` | `POST /api/workspace/stage/remove` | `browser.server._workspace_remove_stage` | `ProjectController.workspace_remove_stage` | same as stage-card `Remove` | workspace bundle |
| Selected Stage | `Reset Override` | `[data-selected-stage-action="reset"]` | `match-view.js` | `POST /api/workspace/stage/override/reset` | `browser.server._workspace_reset_stage_override` | `ProjectController.workspace_reset_stage_override` | same as stage-card `Reset` | workspace bundle |
| Workflow | section shortcut buttons | `[data-workflow-target]` | `match-view.js` | — | — | — | active Match section | browser `localStorage` |
| Workflow | `Open Selected Stage` | `[data-workflow-action="open"]` | `match-view.js` | `POST /api/workspace/stage/open` | `browser.server._workspace_open_stage` | `ProjectController.workspace_open_stage` | same as stage-card `Open` | runtime + stage project open |
| Workflow | `Reset Selected Override` | `[data-workflow-action="reset"]` | `match-view.js` | `POST /api/workspace/stage/override/reset` | `browser.server._workspace_reset_stage_override` | `ProjectController.workspace_reset_stage_override` | same as stage-card `Reset` | workspace bundle |
| Stage card visual | preview tile video | `.match-stage-preview-video` / `preview_url` | `match-view.js` render + `browser.state._build_workspace_context()` | `GET /media/workspace-stage/{stage_id}` | `browser.server._send_workspace_stage_media` | state serialization + stage project resolution helpers | media URL only | no separate persistence; derived from saved stage project |

### Setup-once banner

| Section | Button / control | DOM id / selector | Browser owner | Route | Server handler | Controller method | Data changed | Persistence type |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Setup once | `Apply to All` preview + confirm | `#setup-once-apply` | `app.js` | `POST /api/workspace/apply-from-first/preview`, `POST /api/workspace/apply-from-first` | `_handle_workspace_apply_from_first_preview`, `_handle_workspace_apply_from_first` | `ProjectController.workspace_apply_from_first_preview`, `ProjectController.workspace_apply_from_first` | sibling stage projects, stage output profiles, `first_stage_snapshot`, `inherited_from_first` | workspace bundle + per-stage `project.json` + per-stage `profiles.json` |
| Setup once | `Dismiss` | `#setup-once-dismiss` | `app.js` | — | — | — | banner hidden state | browser runtime only |

### Shared defaults and stage overrides

| Section | Button / control | DOM id / selector | Browser owner | Route | Server handler | Controller method | Data changed | Persistence type |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Defaults | `Aspect Ratio / Framing` | `#shared-frame-profile` | `index.html` + `app.js` | with `Apply Defaults` | `browser.server._workspace_set_defaults` | `ProjectController.workspace_set_defaults` | pending payload → `workspace.shared_defaults.frame_profile` | workspace bundle on apply |
| Defaults | `Export Badges` | `#shared-metric-captions` | `index.html` + `app.js` | with `Apply Defaults` | `browser.server._workspace_set_defaults` | `ProjectController.workspace_set_defaults` | pending payload → `workspace.shared_defaults.metric_caption_preset` | workspace bundle on apply |
| Defaults | `Opening Title` | `#shared-lead-in` | `index.html` + `app.js` | with `Apply Defaults` | `browser.server._workspace_set_defaults` | `ProjectController.workspace_set_defaults` | pending payload → `workspace.shared_defaults.lead_in_card` | workspace bundle on apply |
| Defaults | `Your Logo` | `#shared-brand-mark` | `index.html` + `app.js` | with `Apply Defaults` | `browser.server._workspace_set_defaults` | `ProjectController.workspace_set_defaults` | pending payload → `workspace.shared_defaults.brand_mark` | workspace bundle on apply |
| Defaults | `Apply Defaults` | `#shared-defaults-apply` | `app.js` | `POST /api/workspace/defaults` | `browser.server._workspace_set_defaults` | `ProjectController.workspace_set_defaults` | `MatchWorkspace.shared_defaults`, `updated_at` | workspace bundle |
| Defaults | `Reset` | `#shared-defaults-reset` | `app.js` | `POST /api/workspace/defaults/reset` | `browser.server._handle_workspace_defaults_reset` | `ProjectController.workspace_reset_defaults` | clears `MatchWorkspace.shared_defaults` | workspace bundle |
| Overrides | `Override Aspect Ratio / Framing` | `#override-frame-profile` | `match-view.js` + `app.js` | with `Apply Override` | `browser.server._workspace_set_stage_override` | `ProjectController.workspace_set_stage_override` | pending payload → `StageEntry.override_values.frame_profile` | workspace bundle on apply |
| Overrides | `Override Export Badges` | `#override-metric-captions` | `match-view.js` + `app.js` | with `Apply Override` | `browser.server._workspace_set_stage_override` | `ProjectController.workspace_set_stage_override` | pending payload → `StageEntry.override_values.metric_caption_preset` | workspace bundle on apply |
| Overrides | `Apply Override` | `#override-apply` | `app.js` | `POST /api/workspace/stage/override` | `browser.server._workspace_set_stage_override` | `ProjectController.workspace_set_stage_override` | selected stage `override_values`, stage status, `updated_at` | workspace bundle |

### Match Recap

| Section | Button / control | DOM id / selector | Browser owner | Route | Server handler | Controller method | Data changed | Persistence type |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Recap | `Select All` | `#recap-select-all` | `match-view.js` → `renderRecapPanel()` | — | — | — | `recapPanelState.selectedStageIds` | browser runtime only |
| Recap | `Select None` | `#recap-select-none` | `match-view.js` | — | — | — | `recapPanelState.selectedStageIds` | browser runtime only |
| Recap | stage include checkbox | `.recap-stage-check` | `match-view.js` | — | — | — | `recapPanelState.selectedStageIds` | browser runtime only |
| Recap | reorder drag handle / `↑` / `↓` | `.match-recap-stage-row`, `[data-stage-move]` | `match-view.js` | — | — | — | `recapPanelState.stageOrder` | browser runtime only |
| Recap | `Subtitle` | `.recap-stage-subtitle` | `match-view.js` | — | — | — | `recapPanelState.stageOptionsById[stage_id].subtitle` | browser runtime only |
| Recap | `Gain` | `.recap-stage-gain` | `match-view.js` | — | — | — | `recapPanelState.stageOptionsById[stage_id].audioGain` | browser runtime only |
| Recap | `Mute audio` | `.recap-stage-mute` | `match-view.js` | — | — | — | `recapPanelState.stageOptionsById[stage_id].audioMuted` | browser runtime only |
| Recap | `Transition` | `#recap-transition` | `match-view.js` | with `Render Recap` | `_handle_workspace_recap_render` | `ProjectController.workspace_recap_render` | pending recap transition | no persistence until render |
| Recap | `Result Card` | `#recap-result-card` | `match-view.js` | with `Render Recap` | `_handle_workspace_recap_render` | `ProjectController.workspace_recap_render` | pending recap result-card mode | no persistence until render |
| Recap | `Render Recap` | `#recap-render` | `match-view.js` | `POST /api/workspace/recap/render` | `browser.server._handle_workspace_recap_render` | `ProjectController.workspace_recap_render` | recap temp sequence, optional stage variants, optional result cards, final `recap.mp4` | output file in workspace root |

### Stage Composite

| Section | Button / control | DOM id / selector | Browser owner | Route | Server handler | Controller method | Data changed | Persistence type |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Composite | `Clip path` | `#stage-clip-path` | `index.html` + `match-view.js` | with `Add Clip` | `_handle_workspace_stage_clip_add` | `ProjectController.workspace_stage_clip_add` | pending clip source path | browser input state until add |
| Composite | `Angle role` | `#stage-clip-role` | `index.html` + `match-view.js` | with `Add Clip` | `_handle_workspace_stage_clip_add` | `ProjectController.workspace_stage_clip_add` | pending clip role | browser input state until add |
| Composite | `Add Clip` | `#stage-clip-add` | `app.js` | `POST /api/workspace/stage/clip/add` | `browser.server._handle_workspace_stage_clip_add` | `ProjectController.workspace_stage_clip_add` | `StageEntry.clip_sources` | workspace bundle |
| Composite | `↑` / `↓` | row buttons in `renderStageComposite()` | `match-view.js` | `POST /api/workspace/stage/clip/reorder` | `_handle_workspace_stage_clip_reorder` | `ProjectController.workspace_stage_clip_reorder` | clip order in `StageEntry.clip_sources` | workspace bundle |
| Composite | `Angle Align` | row button in `renderStageComposite()` | `match-view.js` | `POST /api/angle/align` | `_handle_angle_align` | `ProjectController.angle_align` | clip `angle_aligned` flags | workspace bundle |
| Composite | `Plan` | row button in `renderStageComposite()` | `match-view.js` | `POST /api/angle/director/plan` | `_handle_angle_director_plan` | `ProjectController.angle_director_plan` | no persisted mutation by itself; reads merged plan | none |
| Composite | `Remove` | row button in `renderStageComposite()` | `match-view.js` | `POST /api/workspace/stage/clip/remove` | `_handle_workspace_stage_clip_remove` | `ProjectController.workspace_stage_clip_remove` | removes one `StageClipSource` | workspace bundle |
| Composite | `Role` | row `select` | `match-view.js` | `POST /api/workspace/stage/clip/update` | `_handle_workspace_stage_clip_update` | `ProjectController.workspace_stage_clip_update` | `StageClipSource.angle_role` | workspace bundle |
| Composite | `Sync offset (ms)` | row `input` | `match-view.js` | `POST /api/workspace/stage/clip/update` | `_handle_workspace_stage_clip_update` | `ProjectController.workspace_stage_clip_update` | `StageClipSource.sync_offset_ms` | workspace bundle |
| Composite | `Audio gain` | row `input` | `match-view.js` | `POST /api/audio/mix` | `_handle_audio_mix` | `ProjectController.audio_mix_set` | `StageClipSource.audio_gain` | workspace bundle |
| Composite | `Mute` | row checkbox | `match-view.js` | `POST /api/audio/mix` | `_handle_audio_mix` | `ProjectController.audio_mix_set` | `StageClipSource.audio_muted` | workspace bundle |
| Composite | `Primary audio` | row checkbox | `match-view.js` | `POST /api/audio/mix` | `_handle_audio_mix` | `ProjectController.audio_mix_set` | `StageClipSource.audio_primary`, clears other primaries | workspace bundle |
| Composite | `Cut slot` / `Start` / `Duration` | row inputs | `match-view.js` | with `Apply Cut` / `Clear Cut` | `_handle_angle_director_override`, `_handle_angle_director_override_clear` | `ProjectController.angle_director_override_cut`, `ProjectController.angle_director_clear_cut` | pending cut override payload | browser input state until apply |
| Composite | `Apply Cut` | row button | `match-view.js` | `POST /api/angle/director/override` | `_handle_angle_director_override` | `ProjectController.angle_director_override_cut` | `OutputProfile.angle_director_plan` | per-stage `profiles.json` |
| Composite | `Clear Cut` | row button | `match-view.js` | `POST /api/angle/director/override/clear` | `_handle_angle_director_override_clear` | `ProjectController.angle_director_clear_cut` | removes persisted override from `OutputProfile.angle_director_plan` | per-stage `profiles.json` |

### Batch export and Match settings

| Section | Button / control | DOM id / selector | Browser owner | Route | Server handler | Controller method | Data changed | Persistence type |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Export | queue checkbox | `.batch-export-item input[type=checkbox]` | `match-view.js` + `app.js` | — | — | — | queue selection only | browser runtime only |
| Export | `Select All` | `#batch-select-all` | `app.js` | — | — | — | queue check state | browser runtime only |
| Export | `Select None` | `#batch-select-none` | `app.js` | — | — | — | queue check state | browser runtime only |
| Export | `Output recipe` | `#batch-recipe` | `index.html` + `app.js` | with `Export Selected` | `_handle_workspace_export` | `ProjectController.workspace_export` | pending recipe (`stage_output` / `stage_composite`) | browser runtime until export |
| Export | `Export Selected` | `#batch-export-start` | `app.js` | `POST /api/workspace/export` (one request per checked stage) | `browser.server._handle_workspace_export` | `ProjectController.workspace_export` | export outputs/errors, status text | output files under workspace |
| Match Settings | `Show score badges in the stage list` | `#match-setting-show-score` | `match-view.js` + `app.js` | — | — | — | `showScoreBadges` | browser `localStorage` (`splitshot.match.settings`) |
| Match Settings | `Remember the selected stage while moving through the match` | `#match-setting-remember-stage` | `match-view.js` + `app.js` | — | — | — | `rememberStageSelection` | browser `localStorage` (`splitshot.match.settings`) |

## Developer architecture map

| Feature | Browser UI | JS owner | Route | Server handler | Controller method | Persistence layer | Export / media path |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Match shell navigation | left rail, gear, collapse button | `app.js` (`setWorkspaceSection`, `setWorkspaceRailCollapsed`) | — | — | — | browser `localStorage` | — |
| Workspace lifecycle | top status-bar actions, empty-state `New Match` | `app.js`, `match-view.js` refresh | `/api/workspace/new`, `/api/workspace/open`, `/api/workspace/save` | `_new_workspace`, `_open_workspace`, `_save_workspace` | `new_workspace`, `open_workspace`, `save_workspace` | `persistence/workspaces.py`, `LibraryMatchRecord` sync via `persistence/library.py` | saved workspace folder |
| Stage membership | `Stage name`, `Add Stage`, stage-card `Remove` | `app.js`, `match-view.js` | `/api/workspace/stage/add`, `/api/workspace/stage/remove` | `_workspace_add_stage`, `_workspace_remove_stage` | `workspace_add_stage`, `workspace_remove_stage` | `MatchWorkspace.stage_entries`, `stage_order` in workspace bundle | saved workspace folder |
| Stage-open handoff | stage-card `Open`, selected-stage `Open In Stage`, `Return to Match` | `match-view.js`, stage shell | `/api/workspace/stage/open`, `/api/workspace/stage/return` | `_workspace_open_stage`, `_workspace_return_to_workspace` | `workspace_open_stage`, `workspace_return_to_workspace` | workspace metadata + stage `project.json` | `Stages/<stage_id>/project.json` |
| Shared defaults | `Defaults` inspector | `app.js` | `/api/workspace/defaults`, `/api/workspace/defaults/reset` | `_workspace_set_defaults`, `_handle_workspace_defaults_reset` | `workspace_set_defaults`, `workspace_reset_defaults` | `MatchWorkspace.shared_defaults` | affects later export/profile behavior |
| Stage overrides | `Overrides` inspector, stage `Reset` buttons | `app.js`, `match-view.js` | `/api/workspace/stage/override`, `/api/workspace/stage/override/reset` | `_workspace_set_stage_override`, `_workspace_reset_stage_override` | `workspace_set_stage_override`, `workspace_reset_stage_override` | `StageEntry.override_values` in workspace bundle | affects later export/profile behavior |
| Setup-once propagation | banner `Apply to All` | `app.js` | `/api/workspace/apply-from-first/preview`, `/api/workspace/apply-from-first` | `_handle_workspace_apply_from_first_preview`, `_handle_workspace_apply_from_first` | `workspace_apply_from_first_preview`, `workspace_apply_from_first` | workspace bundle + sibling `project.json` + sibling `profiles.json` | stage bundle files under `Stages/` |
| Recap render pipeline | recap controls + `Render Recap` | `match-view.js` | `/api/workspace/recap/render` | `_handle_workspace_recap_render` | `workspace_recap_render` | reads workspace stage projects; writes recap output only | `<workspace>/recap.mp4`, temp files under `<workspace>/.recap-tmp/` |
| Composite clip pipeline | `Composite` lower pane clip controls | `match-view.js`, `app.js` | `/api/workspace/stage/clip/*`, `/api/angle/*`, `/api/audio/mix` | clip / angle / audio handlers | `workspace_stage_clip_*`, `angle_align`, `angle_director_*`, `audio_mix_set` | `StageEntry.clip_sources`, `OutputProfile.angle_director_plan`, per-stage `profiles.json` | composite output later written to `<workspace>/exports/<stage>-stage_composite.mp4` |
| Batch export pipeline | queue + recipe + `Export Selected` | `app.js`, `match-view.js` | `/api/workspace/export` | `_handle_workspace_export` | `workspace_export`, `_workspace_export_stage_output_item`, `_workspace_export_stage_composite_item` | reads workspace bundle, stage projects, stage profiles | `<workspace>/exports/*.mp4`, legacy `<workspace>/<stage>.mp4` fallback |
| Preview tiles | stage-card preview video | `match-view.js` + `browser.state.py` | `GET /media/workspace-stage/{stage_id}` | `_send_workspace_stage_media` | state serialization + stage resolution helpers | derived from workspace + stage project | streamed preview media route |
| Match-only settings | score-badge toggle, remember-stage toggle | `match-view.js` (`persistMatchSettings`) | — | — | — | browser `localStorage` only | — |

## How Match works in code and where

### Browser UI and section ownership

The Match surface is split across three browser files:

- [`../../../../src/splitshot/browser/static/index.html`](../../../../src/splitshot/browser/static/index.html)
  - owns the visible Match DOM: rail, workspace status bar, stage list host, selected-stage pane, recap/composite/export panels, and Match settings.
- [`../../../../src/splitshot/browser/static/views/match-view.js`](../../../../src/splitshot/browser/static/views/match-view.js)
  - owns Match-specific rendering and local panel state.
  - key symbols:
    - `renderWorkspaceStages()`
    - `renderSelectedStagePanels()`
    - `renderRecapPanel()`
    - `renderStageComposite()`
    - `renderBatchExportQueue()`
    - `persistMatchSettings()`
- [`../../../../src/splitshot/browser/static/app.js`](../../../../src/splitshot/browser/static/app.js)
  - owns the shell-level event wiring, Match section routing, picker flows, and the explicit API calls for setup-once, defaults, overrides, batch export, and workspace lifecycle.

### Browser API boundary

All Match routes are dispatched in [`../../../../src/splitshot/browser/server.py`](../../../../src/splitshot/browser/server.py).

There are two important route styles:

1. **traditional state-mutating routes**
   - these update the controller and then respond with a full browser state payload.
   - examples: `/api/workspace/new`, `/api/workspace/defaults`, `/api/workspace/stage/override`
2. **structured feature routes**
   - these return a feature-specific JSON object instead of a full browser state.
   - examples: `/api/workspace/export`, `/api/workspace/recap/render`, `/api/angle/director/plan`

That split matters when you debug the browser because not every Match action is a full-state owner.

### Controller ownership

[`../../../../src/splitshot/ui/controller.py`](../../../../src/splitshot/ui/controller.py) is the main mutation boundary.

Important Match methods:

- workspace lifecycle
  - `new_workspace`
  - `open_workspace`
  - `save_workspace`
- stage membership and handoff
  - `workspace_add_stage`
  - `workspace_remove_stage`
  - `workspace_open_stage`
  - `workspace_return_to_workspace`
- inheritance model
  - `workspace_set_defaults`
  - `workspace_set_stage_override`
  - `workspace_reset_stage_override`
  - `workspace_reset_defaults`
  - `workspace_apply_from_first_preview`
  - `workspace_apply_from_first`
- recap and export
  - `workspace_recap_render`
  - `workspace_export`
  - `_workspace_export_stage_output_item`
  - `_workspace_export_stage_composite_item`
- composite editing
  - `workspace_stage_clip_add`
  - `workspace_stage_clip_update`
  - `workspace_stage_clip_remove`
  - `workspace_stage_clip_reorder`
  - `angle_align`
  - `angle_director_plan`
  - `angle_director_override_cut`
  - `angle_director_clear_cut`
  - `audio_mix_set`

### Persistence and model ownership

Model layer:

- [`../../../../src/splitshot/domain/models.py`](../../../../src/splitshot/domain/models.py)
  - `MatchWorkspace`
  - `StageEntry`
  - `StageClipSource`
  - `AngleDirectorCutDecision`
  - `OutputProfile`
  - `LibraryMatchRecord`

Persistence layer:

- [`../../../../src/splitshot/persistence/workspaces.py`](../../../../src/splitshot/persistence/workspaces.py)
  - workspace metadata
  - `Stages/<stage_id>/project.json`
  - `Stages/<stage_id>/profiles.json`
- [`../../../../src/splitshot/persistence/library.py`](../../../../src/splitshot/persistence/library.py)
  - Match library records and metrics
  - proxy paths for library-owned match previews/proxies

### Output and media paths

The current Match controller writes real outputs to these paths:

- batch stage output:
  - `<workspace>/exports/<stage_id>-stage_output.mp4`
- batch stage composite:
  - `<workspace>/exports/<stage_id>-stage_composite.mp4`
- recap output:
  - `<workspace>/recap.mp4`
- recap temp files:
  - `<workspace>/.recap-tmp/*`
- preview media route:
  - `/media/workspace-stage/{stage_id}`

## Test crosswalk: buttons and features to code

The table below maps the current Match controls and feature clusters to the tests that prove them. Some tests are direct button-level interaction tests; others are controller, persistence, or static-contract tests.

| Visible control / feature | Tests | Coverage depth | Code path exercised |
| --- | --- | --- | --- |
| Match shell sections, pinned lower-pane contract | `tests/browser/test_browser_interactions.py::test_match_workspace_shell_keeps_selected_stage_detail_and_workflow_visible`; `tests/browser/test_browser_static_ui.py::test_browser_match_workspace_uses_live_preview_tiles_and_pinned_lower_pane_contract`; `tests/browser/test_automation_ui_shell_contracts.py` Match shell assertions | interaction + static contract | `index.html` Match shell + `match-view.js` section rendering + `app.js` Match pane layout |
| `New Workspace`, `Open Workspace`, `Save Workspace` | `tests/browser/test_browser_interactions.py` Match workspace lifecycle tests; `tests/browser/test_workspace_flows.py` workspace save/load persistence cases | interaction + controller/persistence | `app.js` workspace handlers → `/api/workspace/*` → controller lifecycle methods |
| `Add Stage`, stage selection, `Remove` | `tests/browser/test_browser_interactions.py` Match add/select/remove flow tests | interaction | `app.js` + `match-view.js` → `/api/workspace/stage/add` / `/api/workspace/stage/remove` |
| stage-card `Open` and shell `Return to Match` | `tests/browser/test_browser_interactions.py::test_match_workspace_stage_open_and_shell_return_restore_match_context` | interaction | `match-view.js` / stage shell → `/api/workspace/stage/open` / `/api/workspace/stage/return` |
| preview tile video | `tests/browser/test_browser_interactions.py` live preview tile proof; `tests/browser/test_browser_static_ui.py` preview tile contract | interaction + static contract | `browser.state._build_workspace_context()` + `/media/workspace-stage/{stage_id}` + `match-view.js` preview rendering |
| `Apply Defaults` / `Reset` | `tests/browser/test_browser_interactions.py` shared defaults apply/reset coverage | interaction | `/api/workspace/defaults` / `/api/workspace/defaults/reset` → controller inheritance methods |
| `Apply Override` / stage `Reset` | `tests/browser/test_browser_interactions.py` override apply/reset coverage | interaction | `/api/workspace/stage/override` / `/api/workspace/stage/override/reset` |
| `Apply to All` / `Dismiss` | `tests/browser/test_browser_interactions.py` setup-once preview/apply/dismiss flow; `tests/browser/test_workspace_flows.py` apply-from-first controller coverage | interaction + controller/persistence | `/api/workspace/apply-from-first/preview` / `/api/workspace/apply-from-first` → Stage-1 propagation helpers |
| recap stage selection, transition, result-card, `Render Recap` | `tests/browser/test_browser_interactions.py::test_match_workspace_recap_reports_success_and_error_states`; `tests/browser/test_workspace_flows.py::test_workspace_recap_render_uses_transition_and_result_cards`; `tests/browser/test_workspace_export_and_recap.py::test_recap_render` | interaction + controller + real-output proof | `match-view.js` recap panel → `/api/workspace/recap/render` → `workspace_recap_render()` |
| composite clip add/reorder/role-sync-audio editing/plan/cut overrides | `tests/browser/test_browser_interactions.py` composite control tests; `tests/browser/test_workspace_flows.py` stage clip + angle-director persistence tests | interaction + controller/persistence | `/api/workspace/stage/clip/*`, `/api/angle/*`, `/api/audio/mix` → composite controller methods |
| `Select All`, `Select None`, recipe select, `Export Selected` | `tests/browser/test_browser_interactions.py::test_match_workspace_batch_export_queue_select_all_none_and_start`; `tests/browser/test_browser_interactions.py::test_match_workspace_batch_export_reports_errors_truthfully`; `tests/browser/test_workspace_export_and_recap.py::test_multi_stage_batch_export`; `tests/browser/test_workspace_export_and_recap.py::test_stage_composite_recipe_exports_real_multi_video_output`; `tests/browser/test_workspace_export_and_recap.py::test_stage_output_recipe_honors_saved_stage_edit_settings` | interaction + controller + real-output proof | `app.js` batch export loop → `/api/workspace/export` → `workspace_export()` and recipe-specific export helpers |
| Match settings toggles | `tests/browser/test_browser_interactions.py` Match settings local persistence / remember-stage behavior | interaction | `match-view.js.persistMatchSettings()` + `app.js` listeners + local storage |
| control inventory claim for Match | `tests/browser/test_browser_control_coverage_matrix.py` | docs/contract | `docs/project/browser-control-qa-matrix.md` Match row |

## Known caveats

- The current Match UI does **not** expose direct main-stage-list reordering controls; recap and composite clip reordering are the explicit reorderable areas today.
- `Angle Align` currently marks clips aligned and proves the route/flag flow, but it is lighter-weight than a full sync-analysis engine.
- `Plan` is a merge of generated cut suggestions and persisted overrides; it is primarily a planning/inspection path until overrides make it concrete.
- Match settings are browser-local only. They do not persist into the workspace bundle or Stage defaults.
- Some legacy-looking handlers remain in `app.js` (`#match-export`, `#match-name-input`) even though the current Match DOM and workflow use the lower-pane batch export and workspace lifecycle controls instead.
- Seam ID `DEV-107.root_shell_compat`: the DEV-107 shell coverage now includes the retained host open-project callback, direct Performance-library `renderAutomationSurface` / `selectedLibraryRecord` consumers, and the Match workflow guardrails for open/return, setup-once, and pinned lower-pane truth.
