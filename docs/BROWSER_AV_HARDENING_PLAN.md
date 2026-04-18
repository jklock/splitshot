# Browser AV Hardening Plan

Last updated: 2026-04-16

## Current Decision

- Browser review must keep a single playback clock per stage stream.
- Browser audio compatibility belongs on the server, not in a hidden secondary media element.
- For PCM audio inside MOV/MP4 containers, the browser server should create a compatibility preview that copies the video stream and transcodes only the audio stream.
- The browser should use that preview only when the preview video timeline matches the source video timeline closely enough for review overlays and timing tables to stay exact.

## Audit Summary

- Recent Firefox/browser regression work introduced a hidden `/media/primary-audio` sidecar with forced resynchronization from the browser client.
- Runtime logs from 2026-04-16 showed that path repeatedly creating and replaying a WAV sidecar while Firefox reported `mozHasAudio: false` on the visible video element.
- Git history showed the earlier browser client state did not have a hidden primary-audio playback clock, which explains why AV behavior felt more stable before the sidecar landed.
- Direct FFmpeg and ffprobe experiments on `Stage1.MP4` showed that a compatibility preview with copied video plus transcoded AAC audio preserved the effective video review timeline closely enough to replace the sidecar approach.

## Implemented Now

- `BrowserControlServer` now enables validated browser media proxying by default.
- `/media/primary` serves a same-element compatibility preview for unsupported audio only when the preview passes video timeline validation.
- Hidden `primary-audio` browser markup and all client-side preview sync logic have been removed.
- Browser review overlay timing continues to follow the visible video element via the existing displayed-frame timing path.
- Regression tests now cover preview creation, preview rejection fallback, and source passthrough when audio is already browser-safe.

## Remaining Work

1. Real clip runtime audit
   - Validate `Stage1.MP4` plus at least two representative real match clips in Firefox, Chromium, and WebKit.
   - Capture logs for initial load, seek, pause/resume, mute/unmute, and final-shot overlay timing.

2. Stronger preview validation
   - Keep copy-safe video codecs on `-c:v copy` only.
   - If a future clip requires video re-encoding, expand validation from stream metadata to sampled packet PTS checks before allowing browser review to use that preview.

3. Failure policy
   - Surface a user-visible status when compatibility preview validation fails so missing browser audio is diagnosable instead of silent.
   - Decide whether a manual debug-only fallback route is still worth keeping for edge clips that cannot be safely proxied.

4. Audit automation
   - Add a scripted browser review audit that opens a clip, seeks to several timestamps, toggles mute, and records activity-log deltas.
   - Fail the audit when media reload churn, unexpected source reattachment, or overlay frame-clock drift is detected.

5. Coverage expansion
   - Add tests for compatibility rejection status/logging.
   - Add tests that guard single-element playback behavior if any browser-specific preview switching is reintroduced later.