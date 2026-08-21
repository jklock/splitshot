# Exhaustive Packaged Release Validation Plan

<!-- Documentation reviewed: 2026-08-12 -->

## Status and Objective

Approved implementation plan. Existing source tests and packaged release-proof flows remain useful, but they do not satisfy this plan until the acceptance criteria below are executable and pass.

Every SplitShot release must test every user-facing feature after the native package is built and installed, using committed real match videos and authentic PractiScore data. Every button, field, option, label, dynamic control, interaction, persistence path, and rendered-output effect must be covered.

The operating systems are independent release targets:

- macOS validates the signed, notarized, installed DMG application on macOS.
- Windows validates the installed NSIS application on Windows.
- Linux validates the packaged AppImage on Linux.

There is no cross-platform output-comparison requirement. Each operating system produces its own complete evidence and pass/fail result. Publication is blocked unless all three pass against the same source commit and committed release-data revision.

## Canonical Real-Data Corpus

The committed release corpus is exactly:

- `tests/release_data/primary.MP4`
- `tests/release_data/secondary.MP4`
- `tests/release_data/practiscore.csv`

These files are release inputs, not secrets. They must be present in a fresh checkout without external downloads, local folders, generated substitutes, or fallback fixtures.

| File | Size | SHA-256 | Validated content |
| --- | ---: | --- | --- |
| `primary.MP4` | 85,871,371 bytes | `46b0afcfbec6f4a555f8abfe7c200cb13d3759d5b245e81d2338a86731825c23` | H.264, 1920x1080, 60 fps, stereo PCM, 21.607467 seconds |
| `secondary.MP4` | 44,662,992 bytes | `a3738264c73537619745a3f13703ac635553c407350d16301cec0acf83a4c0be` | H.264, 1920x1080, 60 fps, stereo PCM, 11.294183 seconds |
| `practiscore.csv` | 3,876 bytes | `aec8ea680b07631f79d5a3615bf68e3ac79656ee5a19e2cdb16d1f6ea4256d52` | Authentic IDPA results, 27 competitors, four stages, 50 columns |

Release validation fails before application launch if a file is missing, untracked, empty, corrupt, or has an unexpected checksum; a video is undecodable, black, effectively blank, missing expected video/audio, or duplicates the other video; the CSV cannot be parsed as the expected IDPA match with 27 competitors and four stages; or tooling substitutes data under `tests/fixtures/`, generated media, or synthetic data.

Changing the corpus is an intentional reviewed change. The table, validation constants, scenario expectations, and visual/output assertions must change in the same commit.

## Package-First Release Architecture

Exhaustive validation runs only against the produced release artifact:

1. Build the native package from the release commit.
2. Sign and notarize where required.
3. Install or mount it through the real distribution path.
4. Launch the installed application.
5. Run the complete real-data feature manifest.
6. Upload the platform evidence bundle.
7. Produce that operating system's independent release decision.

Source unit, integration, browser, and audit suites remain required earlier gates but cannot replace installed-package validation.

A versioned machine-readable manifest describes the product surface and proof. Each OS executes every common product scenario in its installed package plus its platform-specific cases. The aggregator checks completeness, not output equality: each OS must have no failures, skips, or gaps for the exact release commit.

## Exhaustive Runtime Inventory

The validator inventories the installed application's live UI after real data loads. It must include:

- every pane and rail destination;
- every static and dynamically generated button or row action;
- every text, number, color, file, range, checkbox, radio, and other input;
- every selector and every meaningful option;
- every disclosure, workbench, tab, modal, and dialog action;
- every draggable/resizable overlay, marker, boundary box, pane, rail, and waveform control;
- every table action, keyboard action, context action, and transport control;
- every label, heading, help string, status, progress message, validation message, tooltip, placeholder, accessible name, and dynamic value;
- every enabled, disabled, selected, hidden, visible, loading, success, empty, and error state users can encounter; and
- enough dynamic instances to prove stages, sources, shots, markers, text boxes, competitors, bars, proposals, profiles, and Queue rows.

Every discovered identity maps to an executable case. An unknown control, unmapped identity, unexpected hidden control, skipped case, or unexercised dynamic family fails that OS release.

## Per-Control Proof Contract

### Buttons and actions

- Invoke each exactly once and assert immediate result and request count.
- Exercise enabled, disabled, unavailable, confirm, cancel, close, undo, restore, delete, reset, and retry paths.
- Retries or repeated clicks may not conceal a broken first interaction.

### Fields and options

- Text/number fields: valid entry, replacement, supported clearing, boundaries, invalid input, formatting, clamping, validation, preview, persistence, and exported effect.
- Checkboxes/radios: every state and dependent-control change.
- Selectors: every meaningful option, option text, persisted value, and conditional visibility.
- Sliders: minimum, representative middle, and maximum.
- Ordinary saves must preserve the active control rather than replacing it.

### Dragging, layout, text, and accessibility

- Test center, corners, bounds, resize limits, and outside-element pointer release.
- Coordinates must use the rendered video frame, not the surrounding stage.
- Portrait and landscape media must remain fully visible and correctly mapped.
- Assert exact wording, live-data substitutions, control labels, names, values, units, progress, errors, and statuses.
- Reject clipping, unintended truncation, overlap, duplicate labels, inaccessible controls, broken focus order, or missing accessible names/tooltips.

## Full Lifecycle Proof

Every mutating control is followed through all applicable layers:

1. One user interaction.
2. Immediate visible response.
3. Continued DOM connection unless a structural rebuild is intentional.
4. Correct API route, payload, response, and request count.
5. Correct controller/model mutation.
6. Correct project or application data on disk.
7. Correct rerender without snap-back.
8. Correct state after pane navigation.
9. Correct state after stage switching.
10. Correct state after project close/reopen.
11. Correct state after installed-application quit/restart.
12. Correct downstream preview, Metrics, Queue, or rendered-output effect.

Adversarial checks cover rapid edits, reordered responses, focus changes, pane/stage switches during saves, drag release outside the element, stale debounce closures, and older API responses arriving after newer input.

## Required Feature Scenarios

### Shared shell

Test launch intent, project arguments, recent projects, restart, package identity, every rail destination, pane state, resizing, scrolling, locks, modals, color picker, keyboard access, status/progress/errors, and native reveal/open actions. At minimum and desktop window sizes, verify 90%, 100%, 125%, 150%, and 200% effective zoom; launch resets to 90% while deliberate zoom remains usable. Shell, pane, preview, workbenches, and controls remain contained, with scrolling in the owning pane.

### Project and PractiScore

Create, select, open, save, reopen, and delete projects; validate managed folders/output root; import `practiscore.csv`; prove IDPA inference, competitor/place/division/class selection, all four stages, authentic 27-competitor standings, points down, penalties, and persistence. Exercise dashboard/session available, unavailable, authentication, and error states without requiring a live remote match for deterministic proof.

### Media

Add, name, save, select, and delete stages. Add `primary.MP4` as primary media and `secondary.MP4` as secondary media. Test replace, clear, set-primary, remove, re-add, duplicate rejection, in-flight lock, disclosures, stage isolation, preview continuity, project copies, and relative persistence.

### Compose

Test enablement; every default layout, size, position, and reset; every source disclosure, layout, placement, size, opacity, position, and sync field; PiP/other live and final geometry; rapid paired edits; ordering; bounds; and persistence.

### Trim

Test bulk primary/added-media trim, aggregate progress/logs, Apply, Clear, Undo, start/end, nudges, offsets, sync analysis, transport, scrubber, waveform compare/zoom/amplitude/pan, retained duration, naming, repeat apply, derivative selection, reload, and export.

### Score

Test enablement, every preset, every generated score/hit/penalty field and row action, delete/restore, authentic imported reference, and propagation to Review, Metrics, Queue, and output.

### Splits and waveform

Test timing enablement/editor, every timing-event field/action, row edit/lock/delete/restore, shot nudge/selection, waveform shot list/zoom/amplitude/pan, ordering, ShotML values, persistence, Metrics, and rendered timer/split badges.

### Markers

Create every type; test text/assets, timing, style, color, opacity, size, position, quadrant, lock, keyframes, handles, edit/delete, frame-relative center/corners/limits, lifecycle persistence, and encoded appearance.

### Overlay

Test every visibility toggle; split, score, timer, draw, and summary option; typography, colors, sizes, positions, locks, text boxes, badges, Export Badges, portrait/landscape containment, mapping, live preview, and encoded real-data parity.

### Review

Verify every editor is always expanded and minimize controls are absent. Test summary/custom boxes, visibility, source, styles, text, typography, colors, positions, drag, defaults, authentic Division/Class/Overall/result/points-down/penalty text, full lifecycle persistence, and encoded output.

### Export

Create, select, rename, update, apply, save, and delete profiles. Test every profile kind, frame/aspect, preset, codec, quality, frame rate, color space, audio codec/bitrate/sample rate, stage setting, disabled/default state, output root, persistence, and Queue handoff. Export remains settings-only.

### In / Out

Use committed real videos as Intro and Outro in separate cases. Test selection/removal, tabs, independent video/audio fades, manual and match-summary fields, typography, styles, positions, drag, defaults, include choices, active-stage video restoration, and combined-output boundaries.

### Queue

Test membership, queue/requeue/stale/unqueue, Intro/Outro choices, fades, output reveal, Show Log, every status, individual processing, Process as One File, live/final progress, logs, success, validation, and recoverable errors. Progress continues until all requested work finishes; Queue owns execution.

### Metrics

Test match summary, all four stage branches, expand/collapse, scrolling, CSV/TXT exports, authentic 27-competitor cohorts/denominators, and deterministic 8/11 competitor views using real CSV subsets rather than generated competitors. Verify responsive columns, containment, timeline size, rank/`You` axes, selected styling, collision prevention, full-name/value accessibility, propagation, reopen, and restart.

### ShotML

Test every setting and disclosure, threshold, Apply, Reset, Rerun, proposals, Apply/Discard, Reset Defaults, confidence, validation, persistence, rerun results, proposal state, and downstream Splits/Metrics using real media audio.

### Settings

Test every section and global/project field, Save Current, Reset Default, landing/reopen behavior, shell/Compose/Overlay/Review/marker/Export/Queue/In-Out/ShotML defaults, click snapshots, pending edits, new-project seeding, scope, reopen, and restart.

## Rendered-Output Proof

Each OS produces and validates real-video individual and combined outputs. Use packaged/bundled FFprobe to validate streams, codecs, dimensions, frame rate, duration, and audio. Decode deterministic nonblack frames and prove trim/sync, PiP/layout, markers, timer, splits, score, draw, summary, Review, Intro/Outro, fades, match-derived text, portrait/landscape containment, and overlay geometry. Use OCR or equivalent deterministic text proof plus image/geometry assertions.

Black frames, invalid audio, missing overlays, wrong text/duration, clipping, collisions, zoomed/cropped source frames, off-frame controls, or preview/export disagreement fail that OS release.

## Independent OS Gates

### macOS

Build, sign, notarize, staple, mount/install, launch, verify Gatekeeper/codesign, execute the complete manifest, and upload macOS evidence.

### Windows

Build and install NSIS, launch and verify packaged tools/runtime, execute the complete manifest, retain Windows OCR/font proof, and upload Windows evidence.

### Linux

Build and launch the executable AppImage, verify packaged tools/runtime/libraries, execute the complete manifest, and upload Linux evidence.

Test macOS, Test Windows, and Test Linux own their complete platform results. Build success is not release proof. Pull requests run fast source gates plus affected installed-package shards for release-critical changes. Release candidates run every shard. The publishing workflow consumes three complete summaries for the exact tagged commit and cannot begin if any is missing, mismatched, incomplete, skipped, or failing.

## Reports and Artifacts

Each OS uploads package/version/commit/corpus identity; live inventory; inventory-to-case map; action/event/request ledgers; API/model/disk evidence; viewport/zoom/drag/accessibility screenshots; reopen/restart evidence; individual/combined outputs; FFprobe/OCR/frame/geometry/audio results; console/backend/Queue/error logs; and a machine-readable summary.

The summary requires `discovered == mapped == exercised == passed`, `failed == 0`, `skipped == 0`, `gaps == 0`, all artifacts readable, and package/source/corpus identities matching the release candidate.

## Drift Prevention

- New static/dynamic controls automatically fail as uncovered.
- Changed text/options require explicit expectation updates.
- New routes, mutations, settings, persistence fields, or exporters require linked cases.
- Removed controls must disappear from runtime and retained expectations.
- Workflow contract tests prevent removal of browser, installed-package, real-corpus, restart, output-proof, or zero-gap gates.
- Synthetic fallbacks, local paths, external downloads, host-only tools, and pane-open-only screenshots are prohibited for release acceptance.

## Implementation Phases

1. Add checksum/content preflight and rejection tests for `tests/release_data/`.
2. Define the versioned runtime inventory and scenario-manifest schema.
3. Reconcile installed live controls against that manifest.
4. Refactor packaged E2E into independent feature shards with shared real-project setup.
5. Add one-action and full-lifecycle evidence for every control family.
6. Add individual/combined rendered-output assertions.
7. Add packaged quit/restart and project-reopen orchestration per OS.
8. Add platform-specific installation, launch, and evidence collectors.
9. Add per-OS zero-gap aggregators and workflow contract tests.
10. Gate publishing on the three independent passing summaries.
11. Update the QA matrix, Electron release guide, contributor workflow, and release notes.
12. Run all three release candidates, inspect every artifact, repair every gap, then mark this plan implemented.

## Completion Criteria

For one exact release commit, the real corpus passes from a fresh checkout; every installed control/text identity is discovered and mapped; every case executes after installation on every OS; every applicable mutation passes immediate/API/model/disk/navigation/reopen/restart/output proof; every real-video output passes metadata/audio/frame/text/layout/geometry checks; every OS independently reports zero failures, skips, and gaps; every artifact is uploaded and manually reviewed; and Release refuses publication without all three summaries.

Until then, documentation and release notes must accurately describe current packaged coverage and must not claim every feature is validated.
