# Changelog

<!-- Documentation reviewed: 2026-08-12 -->

This file captures launch-grade release notes for SplitShot. Each release section is written to stand on its own as the source for the corresponding GitHub release body.

## v1.0.7

SplitShot 1.0.7 is a major update to the complete match-video workflow. It brings project organization, multi-stage editing, scoring, camera composition, review, output controls, intros and outros, queue processing, metrics, ShotML, and settings into one connected desktop experience.

### Multi-Stage Match Production

- **Build a complete match, stage by stage.** A project can now contain multiple stages, with each stage retaining its own primary footage, added camera angles, trim choices, composition, scoring, timing, markers, overlays, review state, queue status, and output. You can complete one stage, move to another, and return later without losing the work already done.
- **Keep media where it belongs.** The Media workflow follows the active stage. Primary footage and supporting camera angles stay isolated to that stage, so changing stages does not mix footage or output settings from another part of the match.
- **Use a workflow designed for finished production.** The 15-pane rail now follows the complete path from Project and Media through Compose, Trim, Score, Splits, Markers, Overlay, Review, Export, In / Out, Queue, Metrics, ShotML, and Settings.

### Organized, Portable Projects

- **Projects manage their own workspace.** Creating or selecting a project prepares its managed folders and keeps related media, score data, markers, and other project material in the project context.
- **Move and reopen projects with confidence.** Project content is organized around project-relative paths where possible. Reopening a project restores its stages, media, settings, and editing context so work can continue where it stopped.
- **Import with useful defaults.** Project content pickers begin from the active project context, reducing the time spent navigating to the right media or match files.

### Multi-Camera Composition and Trim

- **Add supporting camera angles to every stage.** Use added media for a second shooter angle, side view, range angle, scoreboard view, or any other supporting footage without replacing the primary video.
- **Control each source independently.** Adjust per-source size, position, opacity, placement mode, and synchronization relationship to build picture-in-picture, stacked, or other multi-camera presentations.
- **Trim supporting footage without losing the original.** Set source start and end points, apply the trim for the active stage, review it in the composition, and clear it later when you need to return to the original footage.
- **Keep trimmed sources through output.** The composition, trim, and source settings used during editing follow the stage into review, queue processing, and export.

### Timing, Scoring, and Match Data

- **Work with waveform and synchronization tools.** Review source timing, expand waveform context, analyze supporting footage, and use sync information to align cameras with the primary video.
- **Import authentic PractiScore match context.** SplitShot carries competitors, stage results, penalties, divisions, classes, and standings into the project so score presentation is connected to the footage.
- **Read standings clearly.** Division, class, and overall placements are presented as separate standings with the correct place and cohort total. This makes the result understandable in both the workspace and the rendered video.
- **Use Splits and Metrics for performance context.** Timing, score, and performance information stay attached to the active stage and can be reviewed alongside the actual run.
- **Use ShotML to assist event review.** ShotML helps identify shooter-shot events from footage, providing another layer of timing and performance context for review and presentation.

### Overlays, Markers, and Review

- **Tell the story of the stage on screen.** Add score, timer, split, marker, shot, drawing, text, and review information as part of the visual presentation.
- **Use markers for the moments that matter.** Markers stay associated with the stage and can be used to identify events, call out meaningful moments, and guide review.
- **Create reusable visual treatment.** Text, labels, score display, badges, and metric captions are configured as part of the project workflow rather than rebuilt for every export.
- **Review before rendering.** The Review workflow brings footage, supporting angles, score information, timing, markers, and overlays together so you can check the viewer experience before processing output.
- **See a presentation that matches the output.** Pane layout, preview behavior, review content, and rendered output have been aligned for closer WYSIWYG behavior.

### Output Profiles and Export

- **Create reusable output profiles.** Keep presentation choices for different deliverables, including frame and crop approach, output layout, review source, and visual badge treatment.
- **Prepare exports where the edit already lives.** The Export workflow uses the stage’s actual media, composition, trims, scoring, overlays, and review choices instead of requiring a separate reconstruction step.
- **Produce individual stage outputs or a finished match.** Queue stages for their own output, requeue a stage after changes, or process the match into one combined video.
- **See what happened during processing.** Queue and export views expose status, output location, and processing logs so you can confirm the result and locate the finished file.

### In / Out: Intros and Outros

- **Add match boundaries to a finished production.** Include separate intro and outro media in the project and use them when generating a combined match output.
- **Control fades independently.** Intro and outro media support their own video and audio fade settings for a clean start and finish.
- **Use boundary media as part of the presentation.** Add text and overlay content to intro and outro material, preview it in SplitShot, and include it in the combined Queue result.

### Saved Settings and a More Reliable Editing Experience

- **Save defaults and project-specific choices.** Keep preferred application defaults while preserving the settings that belong to a particular match.
- **Retain work through normal editing.** Settings and controls persist through pane navigation, stage changes, project reopening, and continued work after restart.
- **Edit with stable interaction behavior.** Media selection, queue settings, composition controls, per-source adjustments, Intro / Out controls, output profiles, review state, and overlays have been refined to remain responsive and retain their intended state during normal use.

### Available on macOS, Windows, and Linux

SplitShot 1.0.7 delivers the same complete project, stage, editing, review, and output workflow in desktop packages for macOS, Windows, and Linux.

## v1.0.6

SplitShot 1.0.6 is a Stage-only backport release. It ships trim video derivatives, camera role seeding, output profiles, review source controls, overlay export badges, and full compatibility with the Stage PiP rail — all without Match, Performance Library, Landing, workspace persistence, or shared-shell routing.

### What Changed

- **Trim video derivatives (Phase 03).** Added `trim_video()` in ffmpeg.py for fast non-re-encoding trims via `-c copy`, `trim_merge_source()` in the controller, a `/api/merge/source/trim` route with clear flag, and a Trim UI in merge-pane.js with Start/End number inputs and Apply/Clear buttons.
- **Camera role seeding and sync (Phase 04).** Added role-seeding helpers in pipeline.py — `_normalized_merge_source_angle_role`, `_camera_role_priority`, `_merge_source_role_sort_key`, `_project_merge_seed_mode`, `_resolved_merge_source_mode`, `_resolved_merge_source_slot`, `ResolvedMergeSourcePlacement`, and `_resolved_merge_source_placements`. `_build_multi_pip_merge_plan` and `_build_grid_merge_plan` sort sources by role priority. Added preview reseek throttling (200ms via `secondaryPreviewLastSeekAt` WeakMap) and `syncCorrectionMode` tracking.
- **Shell and waveform (Phase 05).** Waveform multi-track controls (`waveform-mode-single`/`multi`), track list, and segment legend in index.html, app.js, and shell-runtime.js.
- **Output profiles (Phase 06).** `FrameProfile`, `OutputProfileKind`, and `OutputProfile` dataclasses with full serialization. Controller CRUD (`list/create/update/delete/render_output_profiles`) with persistence as `profiles.json`. Five server routes at `/api/output-profiles/{list,create,update,delete,render}`. Output Profiles UI with selector, Create/Delete buttons, and name/type/frame-profile inputs. Pipeline `_frame_profile_to_aspect_ratio` and `compute_crop_box` integration.
- **Review source controls (Phase 07).** Replaced "Show PiP" with "Show added media". Added Review Source selector, Set Source button, and retained/live status text. Review source is stored per output profile via `review_source_id` field and refreshed through `/api/output-profiles/render`.
- **Overlay Export Badges (Phase 07).** Added Export Badges button that saves the current overlay badge state (styles, scoring colors, visibility toggles, locks, typography) to the active output profile's `metric_caption_preset` field.

### Why This Release Exists

The v1.0.6 Stage packet delivers the core editing and export workflow improvements planned for the Stage rail — trim, camera role, output profiles, and review/overlay integration — in a minimal Stage-only backport. No Match, Library, Landing, or workspace features are included.

### Release Proof

This release is backed by passing export tests (46/46), browser control tests (72/72 with 3 pre-existing flaky deselected), and runtime checks on macOS. The canonical test suite passes with all phases verified in dependency order.

## v1.0.5

SplitShot 1.0.5 fixes a critical Windows regression where exported video overlays rendered unreadable tofu boxes instead of text.

### What Changed

- **Fixed exported overlay text rendering as tofu on Windows.** The root cause was that the Qt offscreen platform plugin skips DirectWrite font enumeration on Windows, leaving every font request with zero glyph data regardless of the family name requested. The fix lets Qt use its native `windows` platform plugin for export rendering, which properly initializes the DirectWrite font database.
- **Added explicit Windows font family constants** (`font_policy.py`) and routed all overlay Qt text through a shared font resolver that uses Windows-safe families (`Segoe UI`, `Arial`, `Verdana`, `Tahoma`, `Trebuchet MS` for sans-serif; `Consolas`, `Courier New`, `Lucida Console` for monospace; `Georgia`, `Cambria`, `Times New Roman` for serif).
- **Aligned browser preview font stacks** in `app.js` with the same Windows-safe families so the live preview matches the exported output.
- **Prepended `Segoe UI` and `Consolas` to the CSS body and monospace font stacks** so the entire application UI renders with real Windows fonts instead of falling through unrecognized Apple-specific keywords.
- **Added a Windows OCR proof gate** that runs Tesseract against the bottom half of the exported Clip1 video frame to verify overlay text is human-readable, preventing future font regressions on Windows CI.

### Why This Release Exists

Windows exports could produce a valid MP4 file whose overlay text was unreadable tofu (□ boxes) because Qt had no font glyph data to render. Multiple approaches were attempted — explicit font families, system-font fallback, Helvetica aliasing — but none worked because they all assumed the font database was populated. The offscreen platform plugin was the systemic blocker, and no amount of font-name tuning could compensate for a completely empty font database.

Version 1.0.5 fixes this at the platform level and adds a CI proof gate so the exported overlay text is verified readable on every Windows build going forward.

### Release Proof

This release is backed by five successful Windows CI runs on the packaged NSIS installer artifact, each performing a full E2E export with OCR proof against the exported Clip1 video frame. The OCR proof reads the overlay text and confirms it is human-readable — no tofu, no missing glyphs.

SplitShot 1.0.1 is a packaging and release-proof patch focused on one thing: making the shipped desktop packages actually match the proof claimed by CI.

### What Changed

- Windows packaged runtime no longer depends on a build-machine virtualenv layout.
- The packaged Windows app now uses an app-local Python runtime under `bundle/python`.
- The bundled Windows runtime removes the unused `python3.exe` alias that broke `electron-builder` archive creation in the package-native E2E path.
- Packaged artifact validation now launches the real release artifact on every platform:
  - Windows installed NSIS app
  - macOS DMG app
  - Linux AppImage
- The packaged validation harness no longer depends on shelling out to `uv` from inside the validation subprocesses.

### Why This Release Exists

The 1.0.0 line could report green CI while still leaving a gap between what was tested and what users actually downloaded. In particular, Windows could pass an unpacked-app or installer-exists check while the installed NSIS package still failed for a real user.

Version 1.0.1 closes that gap by moving package proof to the actual Electron output artifacts and by fixing the Windows runtime bundling issues uncovered by that stricter validation path.

### Release Proof

This patch release is backed by fresh package-native E2E validation on the real shipped artifact class for each platform:

- Linux AppImage built, launched, and passed packaged E2E
- macOS DMG app built, launched, and passed packaged E2E
- Windows installed NSIS app built, launched, and passed packaged E2E

### Bottom Line

SplitShot 1.0.1 is the release that turns “the packaged app was tested” into a literal statement about the user-download artifact on macOS, Windows, and Linux.

## v1.0.2

SplitShot 1.0.2 is an emergency macOS packaging fix for a shipped DMG that could install cleanly and then fail before the backend ever started.

### What Changed

- The packaged macOS/Linux Python bundle now includes its own stdlib inside the app-local virtualenv instead of depending on the build machine's managed Python home.
- The packaged Electron launcher now sets `PYTHONHOME` for POSIX app launches so the installed app resolves the bundled stdlib and site-packages from inside the app.
- The bundle verifier now runs under the same packaged `PYTHONHOME` assumptions used by the installed app, so this runtime break is caught before release.

### Why This Release Exists

The published `v1.0.1` macOS DMG could launch the Electron shell and still fail immediately when the bundled Python backend started. The concrete failure was a fatal `ModuleNotFoundError: No module named 'encodings'` because the packaged interpreter still pointed its stdlib lookup at the build host's `uv` Python home.

Version 1.0.2 fixes that packaging error by making the POSIX bundle self-contained and by validating the bundled interpreter under packaged launch conditions before the DMG is produced.

### Release Proof

- Fresh macOS DMG built from the fixed bundle
- Installed DMG app launched and loaded a real project through `scripts/testing/test_packaged_artifact.py`
- Packaged Playwright E2E passed against the generated DMG
- Generated export file verified directly with `ffprobe` as a 4.0 second MP4 containing H.264 video and AAC audio

### Bottom Line

SplitShot 1.0.2 is the macOS release that fixes the broken packaged backend bootstrap and restores a working downloadable DMG.

## v1.0.4

SplitShot 1.0.4 is the packaged-proof cleanup release that turns the repaired desktop pipelines into a clean cross-platform release signal instead of a green run with hidden warning debt.

### What Changed

- Packaged Playwright E2E now uses platform temp directories consistently for project, log, and export paths.
- Packaged Linux validation now extracts the AppImage during install setup and injects the bundled `ffprobe` into the validator environment before E2E runs.
- Packaged E2E now drives merge and PractiScore imports through the real browser file inputs instead of bypassing the app with direct backend-only uploads.
- The packaged timing check now opens the timing workbench before interacting with waveform cards and timing-event controls, and it verifies event creation against the live browser state.
- Export completion detection now waits on the app’s actual status/export state instead of a non-existent UI sentinel.
- The broader packaged comprehensive verifier now reads the real browser-state contract for merge sources and PractiScore import state.

### Why This Release Exists

Version 1.0.3 fixed the bundle/runtime side of cross-platform packaging, but the proof layer still had stale assumptions:

- Windows and Linux packaged validation had already exposed temp-path and bundled-`ffprobe` harness bugs.
- Even after the pipelines passed, the uploaded artifacts still showed warning noise for merge, PractiScore, timing events, waveform selection, and export completion because the E2E script was checking the wrong browser-state fields or the wrong visible pane.
- The broader packaged verifier also used the wrong state keys, so it could report false failures against a working packaged app.

Version 1.0.4 closes those proof gaps so the packaged app is exercised through the real UI surfaces and the validation scripts read the same state contract the app actually exposes.

### Release Proof

- Local packaged macOS smoke launch passed against `SplitShot.app`
- Local packaged macOS release-gate E2E passed with:
  - primary upload
  - `3` detected shots
  - waveform selection
  - real export file creation
  - packaged `ffprobe` validation
  - PractiScore import
  - merge source creation
  - timing-event creation
- Local packaged macOS comprehensive packaged proof passed `8/8` checks after the harness/state-contract fixes
- Cross-platform GitHub Actions package-validation matrix passed for:
  - macOS DMG
  - Windows NSIS installer
  - Linux AppImage

### Bottom Line

SplitShot 1.0.4 is the release where the desktop artifacts and the packaged proof finally line up cleanly across macOS, Windows, and Linux.

## v1.0.3

SplitShot 1.0.3 is the desktop packaging and release-hardening patch that turns the 1.0.2 line into a real clean-runner release for macOS, Windows, and Linux.

### What Changed

- The macOS release workflows now materialize `APPLE_API_KEY` into a temporary `AuthKey_<id>.p8` file before invoking `electron-builder`.
- The macOS workflows now fail fast when notarization secrets are missing or incomplete and release jobs verify the shipped DMG instead of only trusting a signed app bundle.
- Packaged Electron validation now uses tracked media fixtures under `tests/fixtures/media/` instead of ignored local-only videos.
- Packaged E2E now fails immediately if its required fixture is missing instead of warning and continuing with a fake empty file.
- Packaged E2E now clears stale export output and prior log directories before each run so reruns cannot inherit false-positive artifacts.
- Linux packaged startup now resolves bundled `site-packages` explicitly inside the AppImage runtime so bundled imports like `numpy` are available from the shipped artifact.
- Bundle verification is now fatal during packaging, so a broken packaged Python runtime cannot be emitted as a “successful” artifact.
- The Electron package, test, build, and release workflows now run a static CI-input verifier before packaging or validation work so missing tracked fixtures fail fast.

### Why This Release Exists

Version 1.0.2 fixed the original packaged backend bootstrap problem, but the release line still had multiple proof gaps:

- macOS was signed but not properly notarized
- packaged validation depended on ignored local-only media files
- reruns could reuse stale E2E artifacts
- Linux could still package an AppImage whose bundled backend failed to import `numpy` on a clean runner

Version 1.0.3 closes those gaps by fixing the notarization path, moving packaged proof inputs onto tracked fixtures, hardening the E2E harness, and fixing the Linux packaged runtime import path.

### Release Proof

- Fresh macOS DMG package job passed and fresh DMG validation plus packaged E2E passed on a clean runner
- Fresh Windows NSIS package job passed and fresh installed-package validation plus packaged E2E passed on a clean runner
- Linux packaging was repaired to expose bundled `site-packages` and to fail packaging immediately if bundled-runtime verification breaks
- The Electron CI verifier now confirms required packaged-test fixtures are tracked and rejects local-only fixture references before package work starts

### Bottom Line

SplitShot 1.0.3 is the release that hardens SplitShot’s desktop delivery path end to end: notarized macOS distribution, real packaged proof inputs, no stale E2E carryover, and a Linux bundle that is required to prove its own packaged Python runtime before shipping.

## v1.0.0

SplitShot 1.0.0 is the first public release of a local-first competition shooting video analysis workstation built to get a shooter, coach, or editor from raw stage footage to a scored, reviewed, and export-ready presentation without handing the core workflow to a cloud service.

### What SplitShot Is

SplitShot is a desktop-delivered, browser-first app for reviewing competition shooting runs. It combines timing analysis, manual correction, scoring, PractiScore context, overlays, review callouts, PiP composition, metrics, and final export in one project model so the same corrected run state drives every downstream surface.

This release is for people who need more than a timer readout or a generic video editor:

- shooters reviewing stage execution
- coaches breaking down transitions and split behavior
- match video editors building annotated exports
- developers and fork owners who want a local-first foundation for shooting-analysis tooling

### What Shipping 1.0.0 Means

Version 1.0.0 is the point where SplitShot stops being a loose development artifact and becomes a real release line with:

- cross-platform packaged releases for macOS, Windows, and Linux
- a stable `.ssproj` project model that carries timing, scoring, overlay, PiP, review, and export state together
- a browser shell that can be used from source or from the Electron app
- a validated release path backed by CI, packaged-app smoke checks, and end-to-end testing
- a user-facing documentation set and maintainer reading path that explain how to install, use, test, extend, and ship the project

### Core Features In 1.0.0

#### Local-first project workflow

SplitShot keeps the entire working set on the local machine. Primary footage, imported scoring context, timing corrections, overlay state, and export settings live inside or alongside the project bundle instead of being sent to a hosted analysis service. That local-first posture is not branding language. It is the operating model of the app.

#### Start beep and shot detection

The ShotML pipeline gives the app a real first pass instead of a blank timeline. SplitShot analyzes the imported stage video, finds the start beep, proposes likely shot events, renders waveform context, and seeds the review workflow with timing candidates that can then be confirmed or corrected.

#### Timing correction that treats review as first-class work

This release is not limited to automatic detection. The Splits and waveform workflow is built around the reality that serious review requires manual intervention. Users can inspect events, drag or nudge timing, add missing shots, remove false positives, and align the project state with what actually happened in the footage.

#### Scoring with official context when needed

SplitShot can operate as a standalone review tool, but 1.0.0 also supports pulling in PractiScore context so the timing review can stay connected to the official stage and competitor record. Ruleset-aware scoring, penalties, result context, and downstream metrics all ride on the same shared project state.

#### Review overlays, markers, and presentation controls

This release includes the presentation layer needed to turn internal review work into something exportable. Timer badges, shot badges, score summaries, review text boxes, visibility controls, marker callouts, and related overlay settings are part of the core workflow rather than sidecar hacks.

#### PiP and multi-angle composition

SplitShot can bring in additional media, align it, and position it as picture-in-picture, side-by-side, or above-below context. The point is not generic compositing. It is to let reviewers show alternate views, transitions, target movement, or supporting material in a timing-aware edit flow.

#### Metrics and export surfaces tied to the same reviewed state

The metrics and export panes consume the same corrected project model used everywhere else. That means timing cleanup, scoring edits, review visibility, PiP alignment, and overlay configuration all roll forward into the final summary and exported video rather than being re-entered in a separate tool.

### The Road To V1

SplitShot did not get to 1.0.0 through one feature drop. The path to V1 was a sequence of hardening passes that turned a working prototype into a releaseable product.

#### 1. Shared project model and browser-first foundation

The early work established the local project bundle, the controller-backed mutation layer, and the browser-first application shell. That foundation matters because it is what lets analysis, scoring, presentation, and export all stay synchronized instead of fragmenting into parallel state.

#### 2. Pane-by-pane workflow maturity

A major part of the project was making each operational pane carry its own weight. Project setup, ShotML, Splits, Score, PiP, Overlay, Review, Export, Settings, and Metrics were not treated as placeholders. They were pushed until the user-visible workflow made sense as a continuous run review path.

#### 3. Scoring and metrics depth

The scoring layer grew from basic result entry into a ruleset-aware surface with PractiScore context and richer metrics output. That included competitor comparison data, metrics enrichment, and the presentation contracts needed to keep scoring visible in review and export surfaces.

#### 4. Browser-shell UX hardening

A large share of the work before V1 was not additive feature work. It was quality work: fixing timing interaction problems, marker UX problems, overlay inheritance bugs, settings persistence, pane ownership, and browser-state correctness so the UI stopped behaving like an internal prototype.

#### 5. Electron packaging and packaged-app parity

Shipping a local-first app seriously meant proving it outside the source tree. The Electron work was not just packaging. It included launch-intent handling, bundled runtime validation, packaged-app audits, platform-specific build fixes, FFmpeg/FFprobe bundling correctness, signing work on macOS, and repeated parity checks between source and packaged behavior.

#### 6. Cross-platform CI, smoke, and E2E proof

One of the biggest V1 milestones was turning the release path into something defensible. The project now has platform-separated test/build workflows, packaged-app smoke paths, and full end-to-end checks that exercise real packaged applications on GitHub-hosted runners. That is what makes “macOS, Windows, and Linux all ship” a release fact instead of a README aspiration.

#### 7. Documentation and onboarding completion

The final V1 push also included a real documentation pass: user-first install guidance, per-platform local-use instructions, refreshed screenshots, pane-level user docs, subsystem READMEs, architecture maps, test guides, and release-maintainer documentation. That work matters because V1 is not just about the current maintainer being able to run the project. It is about new users and fork owners knowing where to start.

### Why This Release Is Trustworthy

SplitShot 1.0.0 is backed by more than a version bump.

- source runtime checks validate the local toolchain and required assets
- test workflows run on Linux, macOS, and Windows
- packaged-app smoke and E2E coverage exists for Electron delivery paths
- the release workflow now produces all three platform artifacts from one canonical publish path
- the release notes and maintainer docs are tracked in-repo instead of living as throwaway UI text

### Platform Availability

Every 1.0.0 release includes:

- macOS DMG
- Windows installer
- Linux AppImage

SplitShot can also be run directly from source with `uv run splitshot`, and the Electron shell can be launched locally from the repository for development and packaging work.

### Known Constraints

- macOS remains the deepest documented signing and notarization path.
- Browser-first does not mean network-first. The app is still fundamentally local and assumes local media access, FFmpeg tooling, and workstation-class file I/O.
- The app is focused on competition shooting review and export workflows, not generic non-linear editing.

### For Fork Owners And Maintainers

V1 also marks the point where the repository itself becomes easier to adopt:

- the top-level docs route new readers to the right places
- subsystem READMEs identify ownership boundaries and entrypoints
- release governance is documented and reproducible
- the release pipeline uses semver tags and repo-owned notes
- branch strategy is intentionally simple: `main` plus short-lived task branches

If you are forking SplitShot, 1.0.0 is the first release designed to be read, tested, extended, and shipped by someone other than the original author without guesswork.

### Bottom Line

SplitShot 1.0.0 is the moment the project becomes a real product line: local-first, cross-platform, timing-aware, scoring-aware, export-ready, and documented well enough to use or fork without reverse-engineering the entire repository first.
