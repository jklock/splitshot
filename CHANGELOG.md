# Changelog

This file captures launch-grade release notes for SplitShot. Each release section is written to stand on its own as the source for the corresponding GitHub release body.

## v1.0.1

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
