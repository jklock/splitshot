# Motion Tracking in Markers (Popup Bubbles)

## Overview

Motion tracking allows popup markers (also called "popup bubbles") to follow moving objects in video. Instead of staying at a fixed screen position, a marker can be given a **motion path** consisting of timed `PopupMotionPoint` entries. Positions between those points are interpolated with configurable easing. In the shipped V1 browser workflow, users place `Start` and `Finish`, then use `Generate` to try browser-side frame-by-frame normalized cross-correlation (NCC) tracking first, with an evenly spaced linear fallback when tracking cannot lock onto the video detail.

The system is identical in behavior across both the live browser overlay and the Python-side video export pipeline.

### V1 Authoring Model

- `Start` is the popup base position at the beginning of its duration.
- `Finish` is the popup position at the end of its duration.
- `Generate` first calls the browser tracking path and keeps the traced points when tracking succeeds.
- If tracing fails, `Generate` falls back to evenly spaced in-between points between `Start` and `Finish`.
- `Add Detail` splits the largest remaining time gap so one more hand-authored point can be placed.
- The persisted data is still `follow_motion + motion_path`; the simplified V1 UI does not expose a separate advanced keyframe editor.

---

## Architecture

| Layer | Files | Role |
|-------|-------|------|
| **Data model** | `src/splitshot/domain/models.py` | `PopupMotionPoint`, `PopupBubble`, `PopupTemplate` dataclasses + serialization |
| **Python rendering** | `src/splitshot/presentation/popups.py` | Position interpolation, easing, visibility checks |
| **Overlay export** | `src/splitshot/overlay/render.py` | Paints motion-aware popup badges onto video frames for export |
| **Backend controller** | `src/splitshot/ui/controller.py` | Handles save/load of popup data including motion paths |
| **Settings** | `src/splitshot/config.py` | Persists `marker_template` with `follow_motion` default |
| **Persistence** | `src/splitshot/persistence/projects.py` | Saves/loads popup arrays (including `motion_path`) to `project.json` |
| **Frontend** | `src/splitshot/browser/static/app.js` | Trace-first `Generate`, guided motion editing, drag interaction, overlay rendering |
| **Tests** | `tests/presentation/test_popup_presentation.py` | Validates interpolation, deduplication, and easing modes |

---

## Data Model

### `PopupMotionPoint` (`models.py:448-453`)

```python
@dataclass(slots=True)
class PopupMotionPoint:
    offset_ms: int = 0    # milliseconds from popup start time
    x: float = 0.5         # normalized X position (0-1)
    y: float = 0.5         # normalized Y position (0-1)
    easing: str = "linear" # interpolation mode
```

Each `PopupMotionPoint` is a **keyframe** along the motion path.

### `PopupBubble` — motion-relevant fields (`models.py:456-478`)

```python
@dataclass(slots=True)
class PopupBubble:
    ...
    follow_motion: bool = False                          # master switch for motion tracking
    motion_path: list[PopupMotionPoint] = field(default_factory=list)  # the keyframes
    x: float = 0.5          # base X position (normalized 0-1)
    y: float = 0.5          # base Y position (normalized 0-1)
    quadrant: str = "middle_middle"  # named preset or "custom"
    time_ms: int = 0         # when the popup appears (anchor time)
    duration_ms: int = 1000  # how long the popup is visible
    anchor_mode: str = "time"  # "time" or "shot" (follows a shot event)
```

Key invariant: `follow_motion` auto-defaults to `true` if `motion_path` is non-empty (`models.py:825`, `app.js:3046`).

### `PopupTemplate` (`models.py:482-493`)

```python
@dataclass(slots=True)
class PopupTemplate:
    ...
    follow_motion: bool = False   # default for new popups
```

Stored per-project (`project.popup_template`) and as a global `marker_template` in `AppSettings` (`config.py:147`). Applied to every new popup via `currentPopupTemplate()` (`app.js:3088`).

### Valid Easing Constants (`models.py:655`, `app.js:3111-3114`)

`{"linear", "hold", "ease_in", "ease_out", "ease_in_out"}`

---

## Position Interpolation Algorithm

Both Python (`popups.py:161-191`) and JavaScript (`app.js:3158-3187`) implement the identical algorithm:

```
Input: popup bubble, current video position_ms
Output: (x, y) normalized position

1. Compute base point:
   - If quadrant == "custom": use explicit x/y
   - Otherwise: look up from POPUP_BUBBLE_QUADRANT_POINTS table
2. If NOT follow_motion or no position_ms → return base point
3. elapsed_ms = max(0, position_ms - popup_start_time)
4. Walk sorted motion_path keyframes:
   a. Find segment where elapsed_ms falls between two keyframes
   b. ratio = (elapsed_ms - prev_offset) / (next_offset - prev_offset)
   c. Apply easing function to ratio
   d. Linearly interpolate:
      value = prev + (next - prev) * eased_ratio
   e. If past last keyframe → return last keyframe's position
   f. If at exact keyframe offset → return that keyframe's position
```

### Easing Functions (`popups.py:44-56`, `app.js:3117-3127`)

| Easing | Formula | Effect |
|--------|---------|--------|
| `linear` | `ratio` | Constant speed |
| `hold` | `0 if ratio < 1 else 1` | Instant jump at end |
| `ease_in` | `ratio²` | Starts slow, accelerates |
| `ease_out` | `1 - (1-ratio)²` | Starts fast, decelerates |
| `ease_in_out` | `2·ratio²` for ratio≤0.5, `1-(-2·ratio+2)²/2` for >0.5 | Smooth start & end |

### Quadrant Reference Points (`app.js:2985-2996`)

| Quadrant | x | y |
|----------|---|---|
| `top_left` | 0.125 | 0.125 |
| `top_middle` | 0.5 | 0.125 |
| `top_right` | 0.875 | 0.125 |
| `middle_left` | 0.125 | 0.5 |
| `middle_middle` | 0.5 | 0.5 |
| `middle_right` | 0.875 | 0.5 |
| `bottom_left` | 0.125 | 0.875 |
| `bottom_middle` | 0.5 | 0.875 |
| `bottom_right` | 0.875 | 0.875 |
| `custom` | 0.5 | 0.5 |

---

## Auto-Trace Algorithm

The browser tracking function `autoTracePopupBubbleMotion` (`app.js:4283-4399`) implements a **frame-by-frame normalized cross-correlation tracker** entirely in the browser on an offscreen `<canvas>`. In V1, `Generate` uses this tracer first and only falls back to `generatePopupBubbleMotionPathLinear` when tracing fails or the primary video is unavailable. It does not use WebGL, WASM, or server-side processing.

### Step 1 — Prepare (`app.js:4283-4311`)
- Locate the popup bubble and `<video>` element.
- Compute popup start time (`startMs`) and its base position (with `follow_motion=false`).
- Create an offscreen canvas at a reduced frame size: **max 480px wide** via `popupTraceFrameSize` (line 4043). Minimum 96px in either dimension.

### Step 2 — Extract Reference Patch (`app.js:4321-4337`)
- Seek video to `startMs`, draw frame onto canvas.
- Extract **luma (grayscale)** channel: `L = 0.299R + 0.587G + 0.114B` (`popupTraceLumaFrame`, line 4124).
- Search for the best **28×28 pixel** reference patch via `popupTraceSelectPatch` (line 4183):
  - Within an **18-pixel radius** around the expected center, stepping by **2 pixels**.
  - Score each candidate: `stdDev − distance × 0.35` (`popupTracePatchStrength`, line 4178).
  - This prefers **high-contrast patches close to the expected center**.
- **Abort** if the best patch has `stdDev < 8` — not enough texture to track reliably.
- Record `featureOffset`: the delta between the requested center and the actual patch center (in normalized coordinates). This offset is applied to all subsequent tracked positions to maintain the same relative point on the feature.

### Step 3 — Iterate Through Time (`app.js:4339-4364`)
- Generate sampling offsets via `popupTraceOffsets` (line 4257): evenly spaced at `max(33ms, duration_ms / 20)`, ensuring the final offset covers the full duration (at most ~20 samples).
- For each offset:
  1. Seek the video to `startMs + offsetMs` using `popupTraceSeekVideo` (line 4098) with `await` + `requestVideoFrameCallback` for frame-accurate seeking.
  2. Draw the video frame onto the canvas and extract luma.
  3. Call `popupTraceBestMatch` (line 4231) — **coarse-to-fine search**:
     - **Coarse phase**: Search within a **36-pixel radius** around the previous center, stepping by **2 pixels**. At each position, compute `popupTracePatchCorrelation` (line 4204):
       ```
       NCC = covariance(ref_patch, candidate) / (stddev(ref) × stddev(candidate))
       ```
       Covariance is computed as `Σ((candidateᵢ - mean_candidate) × (patchᵢ - mean_patch)) / N`.
     - **Fine phase**: Refine within a **2-pixel radius** around the best coarse match, stepping by **1 pixel**.
  4. **Abort conditions**:
     - Match score is not finite → immediate failure.
     - Score drops below **0.08** for more than **3 consecutive frames** → failure.
  5. Record the match position, adjusted by `featureOffset`, as a `PopupMotionPoint` with `easing: "linear"`.

### Step 4 — Simplify and Store (`app.js:4365-4383`)
- `popupTraceSimplifyPoints` (line 4268): removes consecutive points where both x and y are within **0.005 normalized units** of each other (near-identical adjacent positions). Always keeps the first and last points.
- The simplified path is normalized (sorted by `offset_ms`, deduplicated by offset) via `normalizePopupMotionPath`.
- Committed to the bubble via `setPopupBubbles()` with `commit: true, rerender: true`.

### Step 5 — Cleanup (`app.js:4390-4398`)
- Restore the video to its original position and playback state (paused or playing).

### Key Hardcoded Parameters

| Parameter | Value | Location |
|-----------|-------|----------|
| Trace frame max width | 480 px | `popupTraceFrameSize` (line 4043) |
| Trace frame min dimension | 96 px | `popupTraceFrameSize` (line 4049-4050) |
| Patch size | 28×28 px | `popupTraceExtractPatch` (line 4155) |
| Initial search radius | 18 px | `popupTraceSelectPatch` (line 4183) |
| Initial search step | 2 px | `popupTraceSelectPatch` (line 4183) |
| Tracking search radius | 36 px | `popupTraceBestMatch` (line 4231) |
| Coarse tracking step | 2 px | `popupTraceBestMatch` (line 4231) |
| Fine tracking step | 1 px | `popupTraceBestMatch` (line 4244) |
| Min patch std dev (abort) | 8 | `autoTracePopupBubbleMotion` (line 4330) |
| Weak match threshold | 0.08 | `autoTracePopupBubbleMotion` (line 4352) |
| Weak match streak limit | 3 frames | `autoTracePopupBubbleMotion` (line 4353) |
| Max samples | `max(33, duration/20)` | `popupTraceOffsets` (line 4259) |
| Simplify threshold | 0.005 normalized | `popupTraceSimplifyPoints` (line 4277) |
| Patch strength distance weight | 0.35 | `popupTracePatchStrength` (line 4180) |

---

## Data Flow

### Creation / Update Flow

```
User action (place Start/Finish, click Generate or Add Detail, drag selected point)
  → Frontend creates/modifies PopupBubble.motion_path
  → normalizePopupBubble() → normalizePopupMotionPath()
  → setPopupBubbles() → callApi("/api/popups", ...)
  → controller.set_popups() (controller.py:2489)
  → _popup_bubble_from_dict() (models.py:808)
  → _normalize_popup_motion_path() (models.py:721)
  → project.touch() → project_changed.emit()
  → save_project() (projects.py:224)
  → _serialize() (models.py:577)
  → written to project.json
```

### Retrieval / Load Flow

```
load_project() (projects.py:232)
  → project_from_dict() (models.py:1087)
  → _popup_bubble_from_dict() (models.py:808)
  → _normalize_popup_motion_path() (models.py:721)
  → State sent to browser via API response
  → normalizePopupBubble() (app.js:3038)
  → normalizePopupMotionPath() (app.js:3023)
  → Rendered via popupBubblePoint() (JS) or popup_bubble_point() (Python)
```

### Storage Format in `project.json`

```json
{
  "popups": [
    {
      "id": "abc123",
      "enabled": true,
      "follow_motion": true,
      "motion_path": [
        {"offset_ms": 0, "x": 0.2, "y": 0.3, "easing": "linear"},
        {"offset_ms": 500, "x": 0.8, "y": 0.9, "easing": "ease_in_out"}
      ],
      "quadrant": "custom",
      "x": 0.2, "y": 0.3,
      "time_ms": 1000,
      "duration_ms": 2000
    }
  ]
}
```

---

## Visualization

### Live Video Overlay (`app.js:11437-11538`)
- `renderPopupOverlay` called on every frame during video playback.
- For each currently visible popup bubble at the current video position:
  - Compute position via `popupBubblePoint(bubble, positionMs)`.
  - Render a positioned `<div>` badge with background color, text, optional image.
  - If the bubble is selected in the editor, also call `renderPopupKeyframeOverlay`.

### Keyframe Path Overlay (`app.js:11383-11435`)
When a popup bubble is selected in the editor:
- **Path segments**: Lines connecting consecutive keyframe positions, rendered as rotated `<div>` elements with class `popup-keyframe-path`.
- **Keyframe handle dots**: Draggable `<button>` elements at each keyframe position with class `popup-keyframe-dot` (and `base` for the initial point at offset 0). Clicking a dot selects that keyframe and seeks the video to its time.

### Motion Guide Editor (`app.js:4401-4472`)
Within the popup bubble card in the markers workbench (`renderPopupBubbleMotionGuide`):
- Lists all keyframes as rows (`popup-motion-point-row`).
- Each row contains: seek button, label, time input, easing dropdown, X/Y number inputs, delete button.
- Changes are applied immediately via `setPopupBubbleMotionPointValue` with live preview (no commit on every keystroke, commit on blur/change).

### Overlay Export (`render.py:349-498`)
- Python-side `paint()` method calls `popup_bubble_point(project, popup, position_ms)` at line 493.
- Same interpolation algorithm, used when rendering video exports server-side with Qt's `QPainter`.

---

## User Interaction: Drag to Create Keyframes

### Base Position Drag (`app.js:11036-11072`)
- User drags the popup badge directly on the video canvas.
- `motionOffsetMs` is computed from the current video position relative to popup start.
- On release (`endPopupBubbleDrag`, line 11109), calls `updatePopupBubbleMotionPoint` which either:
  - Updates the base x/y if `offsetMs <= 0`.
  - Creates/updates a keyframe at `offsetMs` if `offsetMs > 0`.

### Keyframe Handle Drag (`app.js:11005-11034`)
- User drags a `popup-keyframe-dot` handle on the overlay.
- `motionOffsetMs` comes from the handle's `data-popup-keyframe-offset`.
- On release, same flow: `updatePopupBubbleMotionPoint` followed by `callApi("/api/popups", ...)`.

---

## Shot-Linked Popups

Popups can be anchored to shot events (`anchor_mode: "shot"`, `shot_id` set). Their effective start time follows the shot's `time_ms` (via `popupBubbleEffectiveTimeMs`, `app.js:3104`). The auto-trace respects this — it computes `startMs` from the shot time, not from `bubble.time_ms`.

### Copy/Paste Motion Path (`app.js:4002-4041`)
- `copyPopupBubbleMotionFromPrevious`: copies the motion path from the chronologically previous popup bubble.
- `applyPopupBubbleMotionToVisibleShotLinked`: applies the current bubble's motion path to all visible shot-linked popups in the filtered list.

### Path Scaling (`app.js:3129-3136`)
When a popup's `duration_ms` changes and it has an existing motion path, `scaledPopupMotionPathOffsets` proportionally rescales all keyframe offsets to fit the new duration:
```
new_offset = round((old_offset / old_duration) × new_duration)
```

---

## Normalization and Serialization

### Backend (`models.py:700-732`)
- `_normalize_popup_motion_point`: clamps `offset_ms` to ≥0, clamps `x/y` to [0,1], validates easing against `_POPUP_MOTION_EASINGS`, defaults to `"linear"` on invalid.
- `_normalize_popup_motion_path`: filters out `None` entries, sorts by `offset_ms`, deduplicates (last wins for same offset).
- `_popup_bubble_from_dict`: if `follow_motion` is not explicitly provided, defaults to `bool(motion_path)` — i.e. a non-empty motion path implies `follow_motion=true`.

### Frontend (`app.js:3011-3036`)
- `normalizePopupMotionPoint`: same clamping/validation as Python.
- `normalizePopupMotionPath`: same sort + deduplicate.
- `normalizePopupBubble`: auto-sets `follow_motion` to `true` if `motion_path.length > 0` (line 3046), even if `bubble.follow_motion` is `false`.

---

## Visibility (`popups.py:86-88`)

A popup bubble is visible at `position_ms` if:
```
start_ms ≤ position_ms ≤ end_ms
```
Where `start_ms` is the popup's effective time (from shot or `time_ms`) and `end_ms = start_ms + duration_ms`.

---

## Key File Reference

| What | File | Lines |
|------|------|-------|
| `PopupMotionPoint` model | `src/splitshot/domain/models.py` | 448-453 |
| `PopupBubble` model | `src/splitshot/domain/models.py` | 456-478 |
| `PopupTemplate` model | `src/splitshot/domain/models.py` | 482-493 |
| Easing constants | `src/splitshot/domain/models.py` | 655 |
| `_normalize_popup_motion_point` | `src/splitshot/domain/models.py` | 700-718 |
| `_normalize_popup_motion_path` | `src/splitshot/domain/models.py` | 721-732 |
| `_popup_bubble_from_dict` | `src/splitshot/domain/models.py` | 808-835 |
| `_apply_easing` (Python) | `src/splitshot/presentation/popups.py` | 44-56 |
| `popup_bubble_motion_path` (Python) | `src/splitshot/presentation/popups.py` | 136-158 |
| `popup_bubble_point` (Python) | `src/splitshot/presentation/popups.py` | 161-191 |
| `popup_bubble_is_visible_at` | `src/splitshot/presentation/popups.py` | 86-88 |
| Overlay export paint | `src/splitshot/overlay/render.py` | 475-498 |
| `set_popups` controller | `src/splitshot/ui/controller.py` | 2489-2513 |
| `marker_template` in settings | `src/splitshot/config.py` | 147 |
| `_apply_effective_settings_to_project` | `src/splitshot/ui/controller.py` | 3162 |
| Project save/load | `src/splitshot/persistence/projects.py` | 224-239 |
| Quadrant reference table (JS) | `src/splitshot/browser/static/app.js` | 2985-2996 |
| `normalizePopupMotionPoint` / `normalizePopupMotionPath` | `src/splitshot/browser/static/app.js` | 3011-3036 |
| `normalizePopupBubble` | `src/splitshot/browser/static/app.js` | 3038-3069 |
| `currentPopupTemplate` | `src/splitshot/browser/static/app.js` | 3088-3090 |
| `popupKeyframeRatio` (JS easing) | `src/splitshot/browser/static/app.js` | 3117-3127 |
| `scaledPopupMotionPathOffsets` | `src/splitshot/browser/static/app.js` | 3129-3136 |
| `popupBubbleMotionPointAtOffset` | `src/splitshot/browser/static/app.js` | 3138-3156 |
| `popupBubblePoint` (JS interpolation) | `src/splitshot/browser/static/app.js` | 3158-3187 |
| `updatePopupBubbleMotionPoint` | `src/splitshot/browser/static/app.js` | 3189-3202 |
| `popupBubbleKeyframes` | `src/splitshot/browser/static/app.js` | 3919-3924 |
| `addPopupBubbleKeyframeAtPlayhead` | `src/splitshot/browser/static/app.js` | 3947-3966 |
| `deletePopupBubbleKeyframe` | `src/splitshot/browser/static/app.js` | 3968-3980 |
| `copyPopupBubbleMotionFromPrevious` | `src/splitshot/browser/static/app.js` | 4002-4017 |
| `applyPopupBubbleMotionToVisibleShotLinked` | `src/splitshot/browser/static/app.js` | 4019-4041 |
| `popupTraceFrameSize` | `src/splitshot/browser/static/app.js` | 4043-4052 |
| `popupTraceSeekVideo` | `src/splitshot/browser/static/app.js` | 4098-4122 |
| `popupTraceLumaFrame` | `src/splitshot/browser/static/app.js` | 4124-4131 |
| `popupTraceExtractPatch` | `src/splitshot/browser/static/app.js` | 4155-4176 |
| `popupTracePatchStrength` | `src/splitshot/browser/static/app.js` | 4178-4181 |
| `popupTraceSelectPatch` | `src/splitshot/browser/static/app.js` | 4183-4202 |
| `popupTracePatchCorrelation` (NCC) | `src/splitshot/browser/static/app.js` | 4204-4229 |
| `popupTraceBestMatch` (coarse-to-fine) | `src/splitshot/browser/static/app.js` | 4231-4254 |
| `popupTraceOffsets` | `src/splitshot/browser/static/app.js` | 4257-4265 |
| `popupTraceSimplifyPoints` | `src/splitshot/browser/static/app.js` | 4268-4281 |
| `autoTracePopupBubbleMotion` (main) | `src/splitshot/browser/static/app.js` | 4283-4399 |
| `renderPopupBubbleMotionGuide` (editor UI) | `src/splitshot/browser/static/app.js` | 4401-4472 |
| Markers workbench | `src/splitshot/browser/static/app.js` | 5184-5358 |
| `beginPopupBubbleDrag` | `src/splitshot/browser/static/app.js` | 11005-11073 |
| `movePopupBubbleDrag` | `src/splitshot/browser/static/app.js` | 11075-11107 |
| `endPopupBubbleDrag` | `src/splitshot/browser/static/app.js` | 11109-11122 |
| `renderPopupKeyframeOverlay` | `src/splitshot/browser/static/app.js` | 11383-11435 |
| `renderPopupOverlay` (live overlay) | `src/splitshot/browser/static/app.js` | 11437-11538 |
| Tests: motion interpolation | `tests/presentation/test_popup_presentation.py` | 54-74 |
| Tests: easing modes | `tests/presentation/test_popup_presentation.py` | 77-100 |
