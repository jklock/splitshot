# Features from Shooting Cut

Features identified for porting from [Shooting Cut](https://shootingcut.com/) — a
native iOS/macOS competition shooting video editor — into SplitShot.

Scoped per feature: **Stage** (single-run), **Match** (multi-stage), or both.

---

## 1. Auto Trim — Stage / Match

Trim dead time before the start beep and after the last shot, producing a
tight export that starts at the beep and ends at the final shot.

- Configurable pre-beep seconds to keep before the timer beep.
- Configurable post-last-shot seconds to keep after the last detected shot.
- **Stage scope:** trim the single primary video on export.
- **Match scope:** trim each stage clip in a Match Recap stitch.
- Overrides must respect user padding preferences stored in Output Profiles.

---

## 2. Merge (Match-level Recap) — Match

Stitch 2–20 stage videos into one continuous highlight reel.

- Per-clip score subtitles and split times.
- Independent audio control per clip.
- Drag-to-reorder stage clips.
- **Note:** SplitShot v1.1 already has Match Recap (recap assembly from
  workspace stages). Verify gaps: per-clip score overlay, drag reorder,
  independent audio-per-clip.

---

## 3. Split Sync — Stage / Match

Sync two camera angles via the timer beep, offering dedicated layouts.

Shooting Cut layouts:
- Full Screen (9:16 portrait)
- Dual Center HUD
- Dual Top HUD
- Side by Side (16:9)

**Note:** SplitShot has Angle Align (sync offset management) + PiP layouts
(picture-in-picture, side-by-side, above-below). Audit against Shooting
Cut's four specific layouts for parity gaps.

---

## 4. Stage Mix — Stage / Match

Multi-camera editing for 2–3 angles. Assign perspectives (POV, Follow,
Static). The app divides the stage into shooting segments, short moves,
and long moves, cutting to the best angle for each. Manual cut override.

**Note:** SplitShot v1.1 has Angle Director — suggested auto-cut plan
generation for multi-angle composition with manual override support. This
is essentially the same concept. Verify parity and close any gaps.

---

## 5. Intro Title Cards — Stage / Match

Animated overlay cards displayed at the start of the exported video
showing match name, date, shooter info, division, stage name, and
optional custom logo.

- Configurable fields in Output Profiles.
- Animated (fade/slide) or static option.
- **Stage scope:** single-video intro.
- **Match scope:** intro plays once before the first stage in a recap.
- Logo upload / selection from local file.

---

## 6. Custom Watermark — Stage / Match

Overlay a logo image, text, or both on the exported video at a
configurable position and opacity.

- Image watermark from local file (PNG with alpha support).
- Text watermark with font, size, color, and opacity controls.
- Position presets: top-left, top-right, bottom-left, bottom-right, center.
- **Stage scope:** applied to single-video export.
- **Match scope:** applied to recap/composite outputs.
- Store in Output Profile for reuse.

---

## 7. Batch Export — Match

Export multiple outputs from the Match workspace in one pass.

**Note:** SplitShot v1.1 already ships Match batch export — recipe
selection, queue, select-all/none, and result reporting. Verify parity
and close gaps if any.

---

## 8. Score Import — Stage / Match

Import match scores from competition sources.

**Current state:** PractiScore import works (`.psc` files, remote match
search). Missing: ESS (IPSC), HDP, IDPA PDF report import.

---

## 9. Export Ratio — Already Supported

SplitShot already supports output ratios via FFmpeg encoding parameters.
No new work needed.

---

## Appendix: Deferred / Rejected

| Feature | Decision | Reason |
|---|---|---|
| AI Reframe / Portrait Tracking | Rejected | Not a goal per user |
| Social Share (YT/TikTok/FB/IG) | Rejected | Local-first browser app |
| iCloud Sync | Rejected | Local-first by design |
| Detection Quality Telemetry | Rejected | Not applicable |
| Export Diagnostics | Rejected | Not applicable |
| Gun Type Override (Firearm/Airsoft) | Rejected | Out of scope for now |
| Airsoft False-Positive Hints | Rejected | Out of scope for now |
