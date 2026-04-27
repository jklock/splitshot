# Browser Control Coverage Plan

This is the exhaustive control-by-control worklist for the SplitShot browser app.

The QA matrix in [browser-control-qa-matrix.md](browser-control-qa-matrix.md) remains the coverage source of truth. This plan exists to make sure every user-manipulable control has an explicit owner, a current status, and a next test.

For the phase-gated execution plan that defines what counts as truthful full-control end-to-end coverage, see [browser-full-e2e-qa-plan.md](browser-full-e2e-qa-plan.md).

## Rules For This Plan

- A control can be a button, input, select, checkbox, range slider, resize handle, drag target, timeline card, or collapsible section header.
- Dynamic row/card families count as controls too. The plan names the family and the per-row actions that need coverage.
- Display-only labels are omitted unless the label itself is clickable or toggles state.
- Native browser media controls are grouped as a single surface unless SplitShot adds custom handling around them.
- When a control changes, update this document and the QA matrix in the same change.

## Current Baseline

Already covered in focused browser tests today:

- Primary rail tool-button routing and active-tool reload persistence.
- Waveform expand, zoom, amplitude, pan, and shot movement.
- Marker import-selected-shot seek, collapsed navigation, timeline selection, and shot-editor step, duplicate, delete, and close coverage.
- Marker template content, text source, duration, placement, size, and follow-motion defaults on fresh shot-linked markers.
- Review text-box source switching to imported summary, after-final render overrides, custom placement and size, and lock-to-stack editor behavior.
- Layout lock toggle plus rail, waveform, and sidebar resize handle persistence.
- Waveform viewport window drag and reload persistence.
- Timing workbench row lock, adjustment, delete, and restore coverage.
- Scoring workbench row lock, score, penalties, delete, and restore coverage.
- Metrics pane downstream coverage for timing-event ordering plus scoring-row edit and restore propagation.
- Selected-shot nudge and delete actions with downstream metrics updates.
- Settings section toggles with in-session route-stable collapse state.
- Settings import-current and reset-defaults actions for merge/export defaults.
- Settings landing pane and reopen-last-tool defaults state updates.
- Settings default sport, PiP size, export quality, and two-pass updates.
- Overlay visibility and badge toggles.
- Review text-box creation and drag.
- Browser reset-defaults behavior for project/app defaults.
- Rail footer layout and scoring workbench smoke coverage.

The plan below focuses on the controls that are still only smoke/static, presence-only, or missing direct behavior coverage.

## Shared Shell

| Control | Current state | Next test |
| --- | --- | --- |
| Primary rail tool buttons: Project, PiP, Score, Splits, Markers, Overlay, Review, Export, Metrics, ShotML | behavioral | Keep the route-and-persist coverage if a rail item changes its routing or activation rules. |
| Settings gear button | behavioral | Keep the direct Settings-pane routing and persistence assertion with the rail-footer contract test. |
| Rail collapse toggle | behavioral | Keep the collapsed-vs-expanded rail persistence coverage for `splitshot.railCollapsed`. |
| Rail resize handle | behavioral | Keep the drag-persistence coverage if the rail geometry or storage key changes. |
| Layout lock toggle in the video stage | behavioral | Keep the unlock/lock persistence coverage if layout locking changes. |
| Waveform resize handle | behavioral | Keep the drag-persistence coverage if the waveform geometry or storage key changes. |
| Sidebar resize handle | behavioral | Keep the drag-persistence coverage if the inspector geometry or storage key changes. |
| Primary video player controls | behavioral at surface level | Keep at least one browser test that verifies play/pause/seek flows still drive SplitShot state when custom behavior depends on the native player. |

## Video And Waveform

| Control | Current state | Next test |
| --- | --- | --- |
| Waveform canvas | interaction | Keep the existing pan, zoom, amplitude, and shot-drag interaction tests as the guardrail for the canvas. |
| Waveform viewport window and handle | behavioral + interaction | Keep the navigator drag/reload coverage if the waveform viewport model or persistence logic changes. |
| Zoom - / Zoom + | smoke | Keep the smoke check that the buttons remain wired; add a focused state assertion if zoom behavior changes. |
| Amp - / Amp + | smoke | Keep the smoke check that the buttons remain wired; add a focused state assertion if amplitude behavior changes. |
| Reset waveform view | smoke | Add a direct reset-state assertion if the waveform viewport model changes. |
| Select mode / Add Shot mode buttons | interaction | Keep mode-switch coverage in the waveform interaction file and add a state assertion if new waveform modes appear. |
| Expand waveform | smoke | Keep expand/collapse coverage and assert the workbench state survives selection changes. |
| Waveform shot list cards | behavioral | Keep one selection test that proves the cards recenter the waveform and update the selected-shot model. |

## Splits And Scoring

| Control | Current state | Next test |
| --- | --- | --- |
| Splits Edit / Collapse toggle | smoke + behavioral | Keep the workbench open/close smoke and assert expansion survives a route change or rerender. |
| Timing event kind select | behavioral | Keep the inserted-event coverage and extend it if additional kinds change downstream metrics or overlay semantics. |
| Timing event label input | behavioral | Keep the direct label-to-row coverage and extend it if label editing gains more downstream consumers. |
| Timing event position select | behavioral | Keep the placement coverage and extend it for before, between, and after assertions if ordering logic changes. |
| Add Event button | behavioral | Keep the insert-and-metrics propagation coverage if event ordering logic changes. |
| Timing event list remove buttons | behavioral | Keep the delete-event rerender and metrics cleanup coverage if event removal semantics change. |
| Selected-shot nudge buttons (-10, -1, +1, +10 ms) | behavioral | Keep the direct nudge and metrics-propagation coverage, and extend it only if new step sizes appear. |
| Delete Selected Shot | behavioral | Keep the delete-selected and metrics-summary fallback coverage if selected-shot deletion semantics change. |
| Timing table row selection | behavioral | Keep the row-selection behavior covered via the existing interaction and contract tests. |
| Timing workbench row lock button | behavioral | Keep the row-edit coverage if the timing table structure or editing flow changes. |
| Timing workbench adjustment input | behavioral | Keep the commit coverage if timing adjustment parsing or persistence changes. |
| Timing workbench Delete button | behavioral | Keep the delete-row coverage if the editable timing table changes. |
| Timing workbench Restore button | behavioral | Keep the restore-row coverage if ShotML timing restore changes. |
| Score Edit / Collapse toggle | smoke + behavioral | Keep the workbench open/close smoke and the scoring-row behavior test. |
| Enable scoring checkbox | behavioral | Keep the current scoring enable/disable coverage. |
| Preset select | behavioral | Keep the preset change coverage and assert the scoring summary updates. |
| Scoring table row selection | behavioral | Keep the row-selection behavior covered in the scoring contract tests. |
| Scoring workbench row lock button | behavioral | Keep the row-edit coverage if the scoring table structure or editing flow changes. |
| Scoring workbench score select | behavioral | Keep the score-commit and metrics-pane propagation coverage if scoring options or payload shape changes. |
| Scoring workbench penalty inputs | behavioral | Keep the penalty-commit coverage if the scoring penalty model changes. |
| Scoring workbench Delete button | behavioral | Keep the delete-row coverage if the scoring table changes. |
| Scoring workbench Restore button | behavioral | Keep the restore-row coverage if scoring restore changes. |

## Markers, Review, And Overlay

### Marker Authoring And Timeline

| Control | Current state | Next test |
| --- | --- | --- |
| Markers Import Shots | behavioral | Keep the selected-shot import and seek coverage, and extend it if staged-shot selection changes. |
| Markers Add Time Marker | behavioral | Keep the add-marker path covered through the existing browser control tests. |
| Marker authoring collapse toggle | behavioral | Keep the collapse-to-compact-nav coverage and extend it only if expand-state persistence changes. |
| Play Window | behavioral | Keep the selected-marker playback-window coverage and extend it if playback uses a different seek or stop path. |
| Loop | behavioral | Keep the looping-window wrap or stop coverage and extend it if loop state moves out of the timeline controls. |
| Previous / Next compact buttons | behavioral | Keep the collapsed-navigation coverage if filter ordering or wrap behavior changes. |
| Popup timeline bars | behavioral | Keep the timeline selection coverage if bar ordering or selection styling changes. |
| Shot-linked marker list cards | behavioral | Keep the list-card selection coverage if marker reveal or seek behavior changes. |
| Time marker list cards | behavioral | Keep the time-marker list-card select-and-seek coverage and extend it if card sorting or seek timing changes. |
| Open Editor | behavioral | Keep the open-editor coverage if the shot-linked marker editor moves or rerenders differently. |
| Shot Marker Editor Done | behavioral | Keep the close-editor coverage and extend it if selection preservation rules change. |
| Shot Marker Editor Previous Shot | behavioral | Keep the previous-shot stepping coverage if shot-linked editor ordering changes. |
| Shot Marker Editor Next Shot | behavioral | Keep the next-shot stepping coverage if shot-linked editor ordering changes. |
| Shot Marker Editor Duplicate Marker | behavioral | Keep the duplicate-marker coverage if clone selection or placement semantics change. |
| Shot Marker Editor Delete Marker | behavioral | Keep the delete-marker coverage if selection fallback or rerender semantics change. |

### Popup Template Controls

| Control | Current state | Next test |
| --- | --- | --- |
| Template Enabled | missing | Add a test that toggles the imported-shot template on and off. |
| Template Content | behavioral | Keep the fresh shot-linked marker generation coverage if content modes or image fallback behavior changes. |
| Template Text Source | behavioral | Keep the score, shot-label, and custom generated-marker payload coverage; shot-linked live overlay text still resolves from score text today. |
| Template Duration | behavioral | Keep the generated-marker duration coverage if the marker window model changes. |
| Template Placement | behavioral | Keep the generated-marker quadrant coverage if shot-marker default placement changes. |
| Template Width / Height | behavioral | Keep the generated-marker size coverage and live badge-size assertion if popup sizing changes. |
| Template Follow Motion | behavioral | Keep the generated-marker follow-motion default coverage if motion-path defaulting changes. |

### Popup Bubble Cards

| Control | Current state | Next test |
| --- | --- | --- |
| Bubble header button | behavioral | Keep the time-marker card header select-and-seek coverage and extend it if card selection routing changes. |
| Bubble enabled checkbox | behavioral | Keep the live-badge hide-or-show coverage and extend it if disabled bubbles still render elsewhere. |
| Bubble expand/collapse toggle | behavioral | Keep the card-body collapse-or-expand coverage and extend it if toggle actions stop preserving selection. |
| Duplicate | behavioral | Keep the duplicate-card coverage and extend it if cloned popups stop selecting or rendering in the timeline. |
| Remove | behavioral | Keep the remove-card coverage and extend it if deletion fallback or timeline rerender rules change. |
| Bubble name input | missing | Add a name-edit commit test. |
| Bubble text textarea | missing | Add a text-edit commit test. |
| Content type select | missing | Add a content-type switch test. |
| Image path input | missing | Add a path-entry test that preserves the chosen asset path. |
| Browse image button | missing | Add a file-pick test for image selection. |
| Image scale select | missing | Add a cover/contain test. |
| Start mode select | missing | Add a time-vs-shot anchor test. |
| Start time input | missing | Add a start-time commit test. |
| Shot select | missing | Add a shot-anchored selection test. |
| Duration input | missing | Add a duration commit test. |
| Follow motion checkbox | missing | Add a motion-path toggle test. |
| Add Keyframe | missing | Add a keyframe insertion test. |
| Previous Keyframe / Next Keyframe | missing | Add keyframe navigation tests. |
| Copy Prev Motion | missing | Add a motion-copy test from the previous bubble. |
| Apply To Shown Shot Popups | missing | Add a bulk-apply motion test for visible shot-linked popups. |
| Clear path | missing | Add a clear-motion-path test. |
| Placement select | missing | Add a quadrant placement test. |
| X / Y inputs | missing | Add a custom-position test. |
| Width / Height inputs | missing | Add a size commit test. |
| Background color swatch + hex field | behavioral | Review text-box background color-picker and linked hex-input coverage are directly covered. |
| Text color swatch + hex field | behavioral | Review text-box text color swatch and linked hex-input coverage are directly covered. |
| Opacity percent input | behavioral | Review text-box opacity commit and preview update are directly covered. |

### Review Text Boxes

| Control | Current state | Next test |
| --- | --- | --- |
| Show timer / draw / split badges / scoring summary checkboxes | behavioral | Keep the existing behavior coverage and extend it when new preview artifacts appear. |
| Add Custom Box | behavioral | Keep the creation coverage and add a persistence test if the box model changes. |
| Add Summary Box | behavioral | Keep the creation coverage and add a persistence test if the imported-summary model changes. |
| Text box header enable checkbox | behavioral | Keep the enabled-state coverage for rendered review boxes. |
| Text box expand/collapse toggle | behavioral | Keep the editor toggle coverage. |
| Duplicate | behavioral | Keep the duplicate-box coverage. |
| Remove | behavioral | Keep the remove-box coverage. |
| Source select | behavioral | Keep the imported-summary source switch coverage and after-final render override assertion. |
| Lock to shot stack checkbox | behavioral | Keep the lock or unlock coverage and extend it with drag parity if the stack rules change. |
| Text textarea | behavioral | Keep the text-entry coverage and assert rerender preserves the editor state. |
| Quadrant select | behavioral | Keep the custom placement coverage and extend it for additional quadrant rules if placement logic changes. |
| X / Y inputs | behavioral | Keep the custom-position coverage and extend it if overlay frame geometry changes. |
| Width / Height inputs | behavioral | Keep the size commit coverage and rendered-size delta assertion if the review badge sizing model changes. |
| Background color swatch + hex field | missing | Add a color-picker and hex-commit test. |
| Text color swatch + hex field | missing | Add a color-picker and hex-commit test. |
| Opacity percent input | missing | Add an opacity commit test. |
| Rendered text-box drag on stage | behavioral | Keep the existing drag test and add one lock-to-stack variant if the stack rules change. |

### Overlay Controls

| Control | Current state | Next test |
| --- | --- | --- |
| Show overlay checkbox | behavioral | Keep the existing visibility test. |
| Badge size select | behavioral | Keep the badge-size behavior coverage. |
| Badge style select | behavioral | Keep the style-switch coverage. |
| Shot gap input | behavioral | Keep the gap update coverage. |
| Frame padding input | behavioral | Keep the margin update coverage. |
| Shots shown input | behavioral | Keep the max-visible-shots coverage. |
| Quadrant select | behavioral | Keep the quadrant placement coverage. |
| Shot flow select | behavioral | Keep the direction-flow coverage. |
| Custom X / Y inputs | behavioral | Keep the custom-position coverage. |
| Timer X / Y inputs | behavioral | Keep the custom timer-anchor coverage with lock gating and live timer placement. |
| Timer lock checkbox | behavioral | Keep the timer lock-to-stack coverage. |
| Draw X / Y inputs | behavioral | Keep the custom draw-anchor coverage with lock gating. |
| Draw lock checkbox | behavioral | Keep the draw lock-to-stack coverage. |
| Score X / Y inputs | behavioral | Keep the custom score-anchor coverage with lock gating. |
| Score lock checkbox | behavioral | Keep the score lock-to-stack coverage. |
| Bubble width / height inputs | behavioral | Keep the live overlay size override coverage. |
| Font family select | missing | Add a font-family test. |
| Font size input | behavioral | Keep the badge font-size coverage. |
| Bold / Italic checkboxes | behavioral | Keep the badge font-weight and font-style coverage. |
| Badge style grid controls | missing | Timer badge background color-picker live preview and close-commit are directly covered; add per-badge background/text/opacity tests for timer, shot, current shot, and score badges. |

## PiP And Merge

| Control | Current state | Next test |
| --- | --- | --- |
| Add PiP Media | behavioral | Keep the existing merge import coverage. |
| Enable added media export | missing | Add an export-enable toggle test for the merge state. |
| Layout select | missing | Add a layout-switch test for side-by-side, above/below, and PiP. |
| Default PiP size slider | missing | Add a size-slider commit test and verify the label updates with it. |
| Default PiP X / Y inputs | missing | Add coordinate commit tests for new merge items. |
| Merge media card collapse toggle | missing | Add an expand/collapse test for each card family. |
| Merge media card remove button | missing | Add a remove-source test and confirm the list rerenders. |
| Merge media card PiP size slider | missing | Add per-item size change coverage. |
| Merge media card opacity input | missing | Add per-item opacity change coverage. |
| Merge media card PiP X / Y inputs | missing | Add per-item position change coverage. |
| Merge media card sync -10 / -1 / +1 / +10 buttons | missing | Add sync-offset nudge coverage for each delta. |

## Export

| Control | Current state | Next test |
| --- | --- | --- |
| Export preset select | behavioral | Keep the preset-commit coverage. |
| Quality select | missing | Add a quality-switch test and confirm the export payload changes. |
| Aspect ratio select | missing | Add an aspect-ratio test and confirm target dimensions update correctly. |
| Output width / height inputs | missing | Add dimension override tests. |
| Frame rate select | missing | Add a frame-rate test. |
| Video codec select | missing | Add a codec-switch test. |
| Video bitrate input | missing | Add a bitrate commit test. |
| Audio codec select | missing | Add an audio-codec test. |
| Audio sample rate input | missing | Add a sample-rate commit test. |
| Audio bitrate input | missing | Add an audio-bitrate commit test. |
| Color space select | missing | Add a color-space test. |
| FFmpeg preset select | missing | Add a preset-switch test. |
| 2-pass checkbox | missing | Add a two-pass toggle test. |
| Output path input | behavioral | Keep the current output-path flow covered. |
| Browse button | behavioral | Keep the browse-path flow covered. |
| Export Video button | behavioral | Keep the export action covered. |
| Show Log button | behavioral | Keep the log-open flow covered. |
| Export log modal close button | behavioral | Keep the export log modal close, backdrop, and download coverage. |
| Export log modal Export Log button | behavioral | Keep the export log download coverage. |
| Export log modal backdrop | behavioral | Keep the export log backdrop-dismiss coverage. |

## Settings

### Collapsible Sections

Each of these headers is clickable and should keep its collapse state stable across rerender and reopen:

- Global template
- Scoring
- PiP
- Overlay
- Markers
- Export
- ShotML

Direct browser coverage now proves these headers toggle and keep their collapse state when routing away from Settings and back within the same session. Reopen persistence is still unproven.

### Global Template

| Control | Current state | Next test |
| --- | --- | --- |
| Save scope select | smoke | Add a scope-switch test that distinguishes app defaults from folder defaults. |
| Landing pane select | behavioral | Keep the defaults-state coverage and add a fresh-project proof that the chosen landing pane is applied on create or reopen. |
| Reopen the selected pane on new projects checkbox | behavioral | Keep the defaults-state coverage and add a fresh-project proof that disabling reopen resets new projects back to Project. |
| Use Current Project As Defaults button | behavioral | Keep the import-current defaults path covered. |
| Reset Defaults button | behavioral | Keep the reset-defaults coverage already in place. |

### Scoring Defaults

| Control | Current state | Next test |
| --- | --- | --- |
| Default sport select | behavioral | Keep the defaults-state coverage and add a fresh-project proof for USPSA, IPSC, and IDPA. |

### PiP Defaults

| Control | Current state | Next test |
| --- | --- | --- |
| PiP layout select | smoke | Add a default-layout test for side-by-side, above/below, and PiP. |
| PiP size select | behavioral | Keep the defaults-state coverage and add a fresh-project proof for the preset sizes. |
| PiP X input | smoke | Add a default-position test for the X coordinate. |
| PiP Y input | smoke | Add a default-position test for the Y coordinate. |

### Overlay Defaults

| Control | Current state | Next test |
| --- | --- | --- |
| Overlay position select | smoke | Add a default-position test for hidden/top/bottom/left/right. |
| Badge size select | smoke | Add a default-size test for XS through XL. |
| Stage box background color | smoke | Add a color-default test. |
| Stage box text color | smoke | Add a color-default test. |
| Stage box opacity | smoke | Add an opacity-default test. |
| Timer badge background/text/opacity | smoke | Add per-badge default tests. |
| Shot badge background/text/opacity | smoke | Add per-badge default tests. |
| Current shot badge background/text/opacity | smoke | Add per-badge default tests. |
| Score badge background/text/opacity | smoke | Add per-badge default tests. |

### Marker Defaults

| Control | Current state | Next test |
| --- | --- | --- |
| Enabled checkbox | smoke | Add an enabled-default test. |
| Content type select | smoke | Add a content-type default test. |
| Text source select | smoke | Add a text-source default test. |
| Duration input | smoke | Add a duration default test. |
| Quadrant select | smoke | Add a placement default test. |
| Width input | smoke | Add a width default test. |
| Height input | smoke | Add a height default test. |
| Follow motion checkbox | smoke | Add a follow-motion default test. |
| Background color input | smoke | Add a marker-color default test. |
| Text color input | smoke | Add a marker-color default test. |
| Opacity input | smoke | Add a marker-opacity default test. |

### Export Defaults

| Control | Current state | Next test |
| --- | --- | --- |
| Export quality select | behavioral | Keep the defaults-state coverage and add a fresh-project proof for export quality. |
| Export preset select | smoke | Add a preset-default test. |
| Frame rate select | smoke | Add a frame-rate-default test. |
| Video codec select | smoke | Add a video-codec-default test. |
| Audio codec select | smoke | Add an audio-codec-default test. |
| Color space select | smoke | Add a color-space-default test. |
| FFmpeg preset select | smoke | Add an ffmpeg-preset-default test. |
| Two-pass checkbox | behavioral | Keep the defaults-state coverage and add a fresh-project proof for two-pass export defaults. |

### ShotML Defaults

| Control | Current state | Next test |
| --- | --- | --- |
| ShotML threshold input | behavioral | Add browser coverage for the analysis-pane apply/reset path. |

## ShotML

### Section Toggles

Each of these headers is a control and should preserve expanded/collapsed state:

- Threshold
- Beep Detection
- Shot Candidate Detection
- Shot Refinement
- False Positive Suppression
- Confidence And Review
- Timing Changer
- Advanced Runtime

### Top-Level Actions

| Control | Current state | Next test |
| --- | --- | --- |
| Re-run ShotML button | behavioral | Keep the rerun path covered. |
| Reset Defaults button | behavioral | Keep the reset-defaults path covered. |
| Generate Proposals button | behavioral | Keep the proposal-generation path covered. |
| Proposal Apply button | behavioral | Keep the proposal-apply path covered. |
| Proposal Discard button | behavioral | Keep the proposal-discard path covered. |

### Threshold

- detection threshold
- cutoff base
- cutoff span

### Beep Detection

- onset fraction
- search lead ms
- tail guard ms
- fallback window ms
- FFT window s
- FFT hop s
- FFT band min Hz
- FFT band max Hz
- fallback multiplier
- tonal window ms
- tonal hop ms
- tonal band min Hz
- tonal band max Hz
- refine pre ms
- refine post ms
- gap before first shot ms
- exclusion radius ms
- region cutoff base
- region threshold weight
- model boost floor

### Shot Candidate Detection

- minimum shot interval ms
- peak minimum spacing ms
- confidence source

### Shot Refinement

- onset fraction
- pre-window ms
- post-window ms
- midpoint clamp padding ms
- minimum search window ms
- RMS window ms
- RMS hop ms

### False Positive Suppression

- weak onset threshold
- near-cutoff interval ms
- confidence weight
- support weight
- weak support penalty
- suppress close-pair duplicates
- suppress sound-profile outliers

### Confidence And Review

- refinement confidence weight
- support pre ms
- support post ms
- support RMS window ms
- support RMS hop ms
- alignment divisor ms
- alignment multiplier
- profile search radius ms
- profile distance limit
- profile high confidence limit

### Timing Changer

| Control | Current state | Next test |
| --- | --- | --- |
| Proposal row summary text | behavioral | Keep the summary copy covered so it still reflects the proposal payload. |
| Apply button | behavioral | Keep the apply-proposal path covered. |
| Discard button | behavioral | Keep the discard-proposal path covered. |

### Advanced Runtime

- window size
- hop size

## Modals And Native Pickers

| Control | Current state | Next test |
| --- | --- | --- |
| Color picker modal Done button | missing | Add a close-modal test. |
| Color picker modal backdrop | missing | Add a backdrop-dismiss test. |
| Color picker hue slider | missing | Add a hue commit test. |
| Color picker saturation slider | missing | Add a saturation commit test. |
| Color picker lightness slider | missing | Add a lightness commit test. |
| Color picker hex input | missing | Add a hex-entry test. |
| Color picker swatches | missing | Add a swatch-apply test. |
| Export log modal Close button | behavioral | Keep the export log modal close, backdrop, and download coverage. |
| Export log modal backdrop | behavioral | Keep the export log backdrop-dismiss coverage. |
| Export log modal Export Log button | behavioral | Keep the export log download coverage. |
| Primary file input | behavioral via the browse button | Keep it covered through the button that opens it. |
| Merge media input | behavioral via the add-PiP button | Keep it covered through the button that opens it. |
| PractiScore file input | behavioral via the select-file button | Keep it covered through the button that opens it. |

## Acceptance Rule

This inventory is complete only when every row above is either:

- covered by a direct behavior test,
- intentionally covered by a smoke/static test because the control is low risk, or
- explicitly marked as a remaining gap with a named test to add next.

The plan should never be updated by hand-waving a surface away. If a control exists in the UI, it gets a row here.

A full-app end-to-end QA claim requires satisfying the stricter exit criteria in [browser-full-e2e-qa-plan.md](browser-full-e2e-qa-plan.md), not just filling out this inventory.

**Last updated:** 2026-04-24
**Referenced files last updated:** 2026-04-24
