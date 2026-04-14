I reviewed the site and pulled out the concrete feature set it advertises, then translated that into a local-first Python build plan you can hand to another LLM.

What Shot Streamer says it does

Shot Streamer presents itself as a competition shooting video analyzer that can upload a video, automatically detect shots and timer beeps, let the user edit detections on an interactive waveform, add shot-stream overlays, merge two camera angles, score shots with letters like A/C/D/M/NS/MU, calculate Hit Factor with penalties, and export an MP4. It also supports overlay placement at top, bottom, left, or right; merge layouts including side-by-side, above/below, and picture-in-picture; manual sync offset adjustments in 1 ms and 10 ms increments; aspect-ratio export with crop repositioning; and customizable badge appearance for timer, shot, current-shot, and hit-factor badges. The site also states support for common video formats, up to 500 MB uploads, up to 4K input, H.264 MP4 output, and automatic upscaling/frame-rate matching when merging videos of different resolutions or frame rates.  

For your version, the most important difference is architectural: Shot Streamer is web/cloud oriented, with uploads, accounts, saved cloud projects, quotas, subscriptions, and server-side processing language on the site. Your request is for a local Python version, so those cloud/account/billing features should be replaced with local project files, local media storage, and offline processing.  

Below is the handoff spec.

⸻

Local Python clone plan: feature-for-feature Shot Streamer equivalent

1. Product goal

Build a desktop application in Python that reproduces Shot Streamer’s end-user workflow as closely as possible, but runs entirely on the local machine with no cloud dependency.

Primary workflow:
	1.	Open first video
	2.	Run automatic shot + beep detection
	3.	Display playable video plus interactive waveform
	4.	Allow manual shot/beep editing
	5.	Optionally add second video and auto-sync it
	6.	Choose merge layout
	7.	Configure overlay and scoring
	8.	Preview result
	9.	Export MP4 locally
	10.	Save/load project locally for later re-edit and re-export

This matches the workflow described on the site for single-video and merged-video analysis.  

⸻

2. Scope: exact feature parity target

The local app should include all of these user-facing features because the site explicitly advertises them.

A. Video ingest

Support opening:
	•	MP4
	•	MOV
	•	AVI
	•	WMV
	•	WebM if practical
	•	Additional formats FFmpeg can decode

The site explicitly mentions MP4, MOV, AVI, WMV on the guide page and also says “all major video formats including MP4, MOV, AVI, and WebM” on the home page. Output should be H.264 MP4.  

B. Single-video analysis
	•	Load one stage/practice video
	•	Run automatic shot detection
	•	Run automatic timer beep detection
	•	Show detections on waveform
	•	Permit manual add/move/delete of shots
	•	Permit moving beep marker
	•	Show split times and draw time
	•	Show shot count

This is core to the site’s “Upload, AI analyzes, fine-tune with waveform editor” flow.  

C. Dual-video merge
	•	Add second video
	•	Detect beep in both videos
	•	Auto-compute sync offset
	•	Support manual sync offset adjustment
	•	Support swap primary/secondary video
	•	Provide mirrored or shared shot timeline behavior across merged view
	•	Keep timing in milliseconds, not frame indices

The site explicitly advertises dual-camera merge, beep-based sync, manual ±10 ms precision adjustment, swap videos, and timing stored in milliseconds.  

D. Layout options

Support:
	•	Side-by-side / picture-by-picture
	•	Above-below
	•	Picture-in-picture
	•	PiP size presets: 25%, 35%, 50%

These are explicitly listed on the site.  

E. Shot stream overlay
	•	Overlay position: none, top, bottom, left, right
	•	Timer badge
	•	Shot badges for each split
	•	Current-shot badge distinct from regular shot badge
	•	Draw time display
	•	Gradient or styled backgrounds
	•	Overlay visible in preview and export

The site explicitly lists the overlay positions and badge customization categories.  

F. Waveform editor
	•	Full-audio waveform overview
	•	Click/tap to add shot
	•	Drag to move shot
	•	Delete shot
	•	Move beep marker
	•	Playhead display
	•	Double-click seek
	•	Zoom and pan even though not explicitly stated, because practical parity will require it

The site explicitly describes add/drag/remove interactions and waveform control.  

G. Shot scoring
	•	Enable scoring mode
	•	Assign per-shot score letters: A, C, D, M, NS, MU or M+NS support
	•	Set visual position of score letter on video
	•	Animate score letter during playback/export
	•	Track penalties
	•	Calculate Hit Factor automatically
	•	Include score letters and hit factor in export

This is directly described in the site content.  

H. Export
	•	Export H.264 MP4
	•	Quality presets: High / Medium / Low
	•	Aspect ratio export options:
	•	Original
	•	16:9
	•	9:16
	•	1:1
	•	4:5
	•	Crop-box repositioning before export
	•	Preserve overlays and scoring in export
	•	Re-export without redoing analysis if project is saved

The site explicitly describes H.264 MP4 output, export quality presets, aspect-ratio export with crop repositioning, and re-export of saved projects in the Pro description. In a local app this becomes simply “re-export any saved project.”  

I. Preferences / customization
	•	Default shot detection threshold
	•	Default overlay position
	•	Default merge layout
	•	Default PiP size
	•	Default export quality
	•	Badge size: XS/S/M/L/XL
	•	Timer badge background/text/opacity
	•	Shot badge background/text/opacity
	•	Current-shot badge background/text/opacity
	•	Hit-factor badge background/text/opacity
	•	Scoring animation colors by letter
	•	Restore defaults

All of that appears in the settings UI text on the site.  

J. Project management

Replace cloud features with local equivalents:
	•	New project
	•	Save project
	•	Load project
	•	Delete project
	•	Unsaved-changes prompt
	•	Save video analysis data
	•	Save shot times and timer settings
	•	Save overlay and scoring configuration

These are explicitly listed in the site save/load UI copy.  

⸻

3. Things to intentionally remove from the local Python version

Do not build these unless you specifically want them later:
	•	Login / sign-up
	•	Google OAuth
	•	Email verification
	•	Password reset
	•	Subscription management
	•	Cloud storage quotas
	•	Free/pro feature gating
	•	Watermarking tied to paid tier
	•	Server upload/download progress logic
	•	AWS/server privacy flow

These exist on the site because it is a hosted SaaS product, not because they are required for the editing workflow itself.  

⸻

4. Recommended desktop stack

For a serious local Python desktop app, I would have the coding LLM target this stack:
	•	UI: PySide6 (Qt for Python)
	•	Video/audio backend: FFmpeg + ffprobe via subprocess
	•	Frame extraction / image operations: OpenCV + NumPy
	•	Audio extraction / signal processing: librosa, scipy, soundfile, numpy
	•	ML inference for shot/beep detection:
	•	PyTorch if using a custom model
	•	ONNX Runtime if you want lighter deployment
	•	Timeline/waveform rendering:
	•	PyQtGraph for performance
	•	or custom QGraphicsView/QPainter timeline
	•	Persistent config: pydantic + JSON / TOML
	•	Project save format: folder-based bundle with JSON metadata
	•	Export pipeline: FFmpeg filter graphs or frame-composited render + FFmpeg encode
	•	Packaging: PyInstaller or Briefcase

This part is my implementation recommendation, not something the site states.

Why PySide6: you need a real desktop GUI with precise waveform editing, multi-panel layout, fast scrubbing, and custom controls. Tkinter is too limited for a polished feature-for-feature clone.

⸻

5. High-level architecture

Use a modular architecture so another LLM can implement it without turning the project into a monolith.

Core modules

app/
	•	application bootstrap
	•	dependency wiring
	•	settings management
	•	recent projects

domain/
	•	project entities
	•	shot event entities
	•	score entities
	•	merge/layout entities
	•	export entities

media/
	•	video probe
	•	frame reader
	•	audio extractor
	•	thumbnail generator
	•	waveform sampler

analysis/
	•	beep detector
	•	shot detector
	•	threshold/sensitivity logic
	•	auto-sync calculator

timeline/
	•	waveform rendering
	•	shot marker model
	•	playhead control
	•	editing gestures
	•	split time computation

scoring/
	•	score letters
	•	penalties
	•	hit factor computation
	•	score animation model

overlay/
	•	timer badge renderer
	•	shot badge renderer
	•	hit factor badge renderer
	•	score-letter renderer
	•	style/theme system

merge/
	•	dual-video alignment
	•	layout compositing
	•	swap logic
	•	PiP sizing and placement

export/
	•	preview crop calculator
	•	aspect-ratio transforms
	•	composition pipeline
	•	ffmpeg encoder wrapper
	•	progress reporting

persistence/
	•	project save/load
	•	media linking/copying
	•	local asset management

ui/
	•	main window
	•	video preview widget
	•	waveform/timeline widget
	•	split-times table
	•	scoring panel
	•	overlay settings panel
	•	export dialog
	•	preferences dialog
	•	project gallery

⸻

6. Data model

Have the coding LLM use explicit schemas.

Project

Project:
  id: str
  name: str
  created_at: datetime
  updated_at: datetime
  primary_video: VideoAsset
  secondary_video: Optional[VideoAsset]
  analysis: AnalysisState
  scoring: ScoringState
  overlay: OverlaySettings
  merge: MergeSettings
  export: ExportSettings
  ui_state: UIState

Video asset

VideoAsset:
  path: str
  duration_ms: int
  width: int
  height: int
  fps: float
  audio_sample_rate: int
  rotation: int

Analysis state

AnalysisState:
  beep_time_ms_primary: Optional[int]
  beep_time_ms_secondary: Optional[int]
  sync_offset_ms: int
  detection_threshold: float
  shots: list[ShotEvent]

Shot event

ShotEvent:
  id: str
  time_ms: int
  source: Literal["auto", "manual"]
  confidence: Optional[float]
  score: Optional[ScoreMark]

Score mark

ScoreMark:
  letter: Literal["A", "C", "D", "M", "NS", "MU", "M+NS"]
  x_norm: float
  y_norm: float
  animation_preset: str

Scoring state

ScoringState:
  enabled: bool
  penalties: int
  hit_factor: Optional[float]

Overlay settings

OverlaySettings:
  position: Literal["none", "top", "bottom", "left", "right"]
  badge_size: Literal["XS", "S", "M", "L", "XL"]
  timer_badge: BadgeStyle
  shot_badge: BadgeStyle
  current_shot_badge: BadgeStyle
  hit_factor_badge: BadgeStyle
  scoring_colors: dict[str, str]

Merge settings

MergeSettings:
  enabled: bool
  layout: Literal["side_by_side", "above_below", "pip"]
  pip_size: Literal["S", "M", "L"]
  primary_is_left_or_top: bool

Export settings

ExportSettings:
  quality: Literal["high", "medium", "low"]
  aspect_ratio: Literal["original", "16:9", "9:16", "1:1", "4:5"]
  crop_center_x: float
  crop_center_y: float
  output_path: Optional[str]


⸻

7. Detection system plan

The site says it uses ML and allows sensitivity from 0.1 to 0.9, with 95%+ accuracy claims and manual adjustment when needed. Your local clone should preserve the same user-facing model: automatic detection plus human correction.  

I would implement detection in three layers:

Layer 1: deterministic audio preprocessing
	•	Extract mono audio at fixed sample rate, e.g. 16 kHz or 22.05 kHz
	•	Normalize loudness
	•	Generate waveform envelope
	•	Detect transient candidates
	•	Detect likely beep candidate by narrow-band high-energy onset

Layer 2: classifier

Use either:
	•	a lightweight CNN over mel spectrogram windows, or
	•	an ONNX model trained to classify shot, beep, other transient

Layer 3: post-processing
	•	Minimum spacing between shots
	•	Shot clustering suppression
	•	Confidence threshold mapped to user threshold slider
	•	Optional sport profile presets:
	•	handgun outdoor
	•	handgun indoor
	•	rifle outdoor
	•	dry fire / steel / suppressed later

Important behavior

The LLM implementing this should treat the ML detector as assistive, not authoritative. The waveform editor is part of parity, not a fallback hack.

⸻

8. Waveform editor requirements

This is one of the core differentiators and needs to be excellent.

Required interactions
	•	Show full waveform for primary video
	•	Show mirrored/view-only waveform for secondary video in merge mode
	•	Click empty space to add shot
	•	Drag shot marker to new time
	•	Right-click or delete key to remove shot
	•	Shift-click beep marker to move beep
	•	Double-click waveform to seek preview
	•	Drag playhead scrubber
	•	Zoom with mouse wheel or trackpad pinch
	•	Horizontal pan when zoomed
	•	Keyboard nudge selected marker by:
	•	1 ms
	•	10 ms
	•	1 frame

The site explicitly mentions click/add, drag/move, right-click/remove, playhead, and separate view-only waveform behavior for the secondary video.  

Split times table

For each shot:
	•	shot number
	•	absolute time
	•	split from previous
	•	score letter
	•	optional notes/confidence

Also compute:
	•	draw time = first shot - beep
	•	total shots
	•	total time
	•	maybe last shot timestamp

The site explicitly references split times and draw time in overlay/analytics.  

⸻

9. Merge and sync plan

The local clone should follow the behavior the site describes:
	•	Probe both videos with ffprobe
	•	Extract audio
	•	Detect beep in each
	•	Compute sync_offset_ms = secondary_beep - primary_beep
	•	Apply offset at playback and export
	•	If automatic beep detection fails, allow manual offset adjustment in 1 ms and 10 ms increments
	•	Preserve shot timing on millisecond basis

For videos with differing fps/resolution:
	•	match export to higher-quality source, as Shot Streamer says it does
	•	side-by-side: match heights
	•	above-below: match widths
	•	PiP: keep main video native and scale inset

That mirrors the site’s FAQ behavior.  

⸻

10. Overlay system plan

Overlay content
	•	elapsed timer badge
	•	draw-time badge
	•	rolling shot badges showing split times
	•	highlight the current/latest shot with distinct styling
	•	hit-factor badge when scoring is enabled

The site clearly distinguishes timer, shot, current-shot, and hit-factor badges.  

Overlay placement
	•	top
	•	bottom
	•	left
	•	right
	•	none

Overlay styling

Each badge style should support:
	•	background color
	•	text color
	•	opacity level
	•	size preset

Use a renderer abstraction like:

class OverlayRenderer:
    def render(frame: np.ndarray, state: OverlayRenderState) -> np.ndarray: ...

Preview behavior

Preview must match export behavior closely. The site frames these overlays as visible during playback and preserved in exported MP4.  

⸻

11. Scoring system plan

The scoring feature should work exactly like this:
	1.	User enables scoring mode
	2.	User selects a shot in the list or moves playhead to that shot
	3.	User picks a letter: A, C, D, M, NS, MU or M+NS depending on final UI decision
	4.	User clicks on the video to place the score letter location
	5.	During playback/export, the letter animates in and fades out
	6.	Penalties affect hit-factor calculation

The site explicitly describes enable scoring, assign letters, place them on video, animate them, and include hit factor.  

Suggested hit factor formula

The coding LLM should make scoring rules configurable, because point systems differ by discipline/stage configuration. Minimum viable version:
	•	map letters to points with editable defaults
	•	compute total points
	•	subtract penalty points
	•	divide by total time in seconds

Do not hard-code one sport’s rulebook unless you want discipline presets.

⸻

12. Export engine plan

Export path

Use FFmpeg for final encode.

Two possible approaches:

Option A: frame-by-frame composition in Python
	•	decode frames
	•	composite overlays and score letters in Python/OpenCV
	•	write intermediate frames or pipe to FFmpeg

This is easier to reason about, but slower.

Option B: hybrid
	•	precompute shot/overlay timing metadata
	•	use FFmpeg filters where possible
	•	use Python only for generated overlay assets and crop math

This is harder but more efficient.

For an LLM-built v1, I would choose Option A first because it is less brittle.

Quality presets

Implement:
	•	High
	•	Medium
	•	Low

Map these to bitrate / CRF presets.

Aspect ratio export

Implement:
	•	original
	•	16:9
	•	9:16
	•	1:1
	•	4:5

Add:
	•	preview with crop rectangle
	•	drag crop area to reposition
	•	disable obviously destructive ratios for some merge layouts if desired

This matches the site’s aspect-ratio export UI and FAQ.  

⸻

13. Local project format

Replace cloud project storage with a local bundle.

Recommended format:
	•	one folder per project
	•	JSON metadata + optional copied media + thumbnails + cache

Example:

MyProject.ssproj/
  project.json
  primary.mp4
  secondary.mp4
  thumb_primary.jpg
  thumb_secondary.jpg
  waveform_cache_primary.npy
  waveform_cache_secondary.npy
  preview/
  exports/

Alternative:
	•	store only references to external media paths, with optional “copy into project” toggle

Save should include
	•	video file references or copies
	•	analysis data
	•	shot times
	•	timer/beep settings
	•	overlay configuration
	•	scoring configuration
	•	export preferences

That is taken directly from the site’s save-project description, adapted from cloud to local.  

⸻

14. UI layout recommendation

Use a three-pane desktop layout.

Top-left

Video preview

Top-right

Secondary preview or settings tabs depending on mode

Bottom full-width

Interactive waveform/timeline

Right side dock or tab panel
	•	Project
	•	Merge
	•	Overlay
	•	Scoring
	•	Export
	•	Preferences

Bottom table

Split times / scores grid

Main menu
	•	Project
	•	Analyze
	•	Merge
	•	Overlay
	•	Scoring
	•	Layout
	•	Export
	•	Settings
	•	Help

That menu structure mirrors the site’s exposed menu labels closely.  

⸻

15. Implementation phases for the coding LLM

Phase 1: foundation
	•	PySide6 app shell
	•	open video
	•	ffprobe metadata
	•	play video with audio
	•	extract waveform
	•	show playhead and scrubber

Phase 2: analysis
	•	beep detection
	•	shot detection
	•	threshold control
	•	shot markers
	•	split time computation

Phase 3: editing
	•	add/move/delete shots
	•	move beep
	•	keyboard nudging
	•	save/load project

Phase 4: merge
	•	second video import
	•	auto-sync by beep
	•	manual sync offset
	•	side-by-side, above-below, PiP
	•	swap videos

Phase 5: overlay
	•	timer and shot badges
	•	position controls
	•	badge appearance controls
	•	live preview

Phase 6: scoring
	•	per-shot letters
	•	on-video score placement
	•	penalties
	•	hit factor
	•	animated score overlays

Phase 7: export
	•	MP4 encode
	•	quality presets
	•	aspect ratio crop export
	•	progress reporting

Phase 8: polish
	•	preferences defaults
	•	restore defaults
	•	thumbnail gallery
	•	recent projects
	•	performance tuning
	•	packaging

⸻

16. Non-functional requirements

The coding LLM should be told these are mandatory.
	•	Entire app must function offline after install
	•	No account system
	•	No telemetry by default
	•	No cloud upload or remote processing
	•	Project files must be portable between machines
	•	All timestamps stored in milliseconds
	•	UI must remain usable on long videos and 4K clips
	•	Export should survive interruption cleanly and not corrupt source project
	•	Save format must be backward-versioned with schema versioning
	•	All destructive actions need confirmation
	•	Unsaved-changes warning required

⸻

17. Acceptance criteria for parity

Use this as the test checklist.

A build is not “feature-for-feature enough” unless it can do all of the following:
	1.	Load a single shooting video and auto-detect beep + shots.
	2.	Let the user manually add, move, and remove shot markers on a waveform.
	3.	Compute and display split times and draw time.
	4.	Add an overlay in top/bottom/left/right positions.
	5.	Load a second video and auto-sync it from beep timing.
	6.	Let the user manually adjust sync in fine increments.
	7.	Switch among side-by-side, above-below, and PiP layouts.
	8.	Swap primary and secondary videos.
	9.	Enable scoring and assign per-shot letters.
	10.	Place score letters visually on the frame.
	11.	Calculate hit factor with penalties.
	12.	Preview overlays and scoring during playback.
	13.	Export final MP4 with overlays/scoring.
	14.	Export using aspect-ratio crop options.
	15.	Save project locally and reload it later without losing edits/preferences.

⸻

18. Prompt you can give another LLM

Copy this exactly:

Build a local-first desktop application in Python that reproduces the user-facing functionality of Shot Streamer as closely as possible, but without any cloud, account, billing, or server features.

Technical stack:
	•	Python 3.12
	•	PySide6 for desktop UI
	•	FFmpeg/ffprobe for media probing and export
	•	OpenCV, NumPy, SciPy, librosa for media/audio processing
	•	PyQtGraph or equivalent high-performance waveform/timeline rendering
	•	JSON-based project save format

Architecture requirements:
	•	Modular package structure with separate modules for media, analysis, timeline, merge, scoring, overlay, export, persistence, and UI
	•	Strong typed dataclasses or pydantic models for project state
	•	All timestamps stored in milliseconds
	•	Entire app works offline after installation
	•	Local project save/load only

Required features:
	1.	Open a primary video and analyze audio for timer beep and shot detections.
	2.	Show interactive waveform editor with:
	•	click to add shot
	•	drag to move shot
	•	right-click/delete to remove shot
	•	move beep marker
	•	playhead scrubbing
	•	zoom and pan
	3.	Show split times, total shots, and draw time.
	4.	Support second video import for merge mode.
	5.	Auto-sync videos using beep detection.
	6.	Allow manual sync adjustment in very fine increments.
	7.	Merge layouts:
	•	side-by-side
	•	above-below
	•	picture-in-picture
	8.	Support swapping primary/secondary videos.
	9.	Overlay system with positions:
	•	none
	•	top
	•	bottom
	•	left
	•	right
	10.	Overlay content:

	•	timer badge
	•	shot badges
	•	highlighted current-shot badge
	•	hit-factor badge when scoring enabled

	11.	Preferences/customization:

	•	detection threshold
	•	default overlay position
	•	default merge layout
	•	PiP size presets 25%, 35%, 50%
	•	export quality presets high/medium/low
	•	badge size presets XS/S/M/L/XL
	•	customizable colors/text/opacity for timer, shot, current-shot, and hit-factor badges
	•	scoring letter colors
	•	restore defaults

	12.	Scoring mode:

	•	assign score letters per shot
	•	supported letters A, C, D, M, NS, MU, and optionally M+NS
	•	click on video to place score letter location
	•	animate score letters during preview/export
	•	track penalties
	•	compute hit factor

	13.	Export:

	•	H.264 MP4
	•	preserve overlays and scoring
	•	aspect ratio export options original, 16:9, 9:16, 1:1, 4:5
	•	crop-box preview with draggable repositioning

	14.	Local project management:

	•	new/save/load/delete project
	•	unsaved changes prompts
	•	save media references or copied media plus full analysis/overlay/scoring state

	15.	Performance:

	•	support at least 1080p reliably
	•	architecture should be ready for 4K even if export is slower

Implementation approach:
	•	First build a working vertical slice for single-video analysis, waveform editing, and export.
	•	Then add merge mode, overlay system, scoring, preferences, and project persistence.
	•	Write clean, production-style code with comments, type hints, error handling, and modular separation.
	•	Do not stub core features. Implement real working code.
	•	Where ML shot detection is not yet trained, create a pluggable detector interface with a solid deterministic transient-based baseline detector plus a placeholder for ONNX/PyTorch classifier integration.
	•	Use FFmpeg/ffprobe via subprocess wrappers, not shell strings concatenated unsafely.
	•	Provide the full source tree.
	•	Provide a runnable MVP first, then iterate feature-by-feature until all requirements above are implemented.If you want, I can turn this into an even tighter engineering PRD with explicit screen-by-screen UI requirements and JSON schemas.

**Last updated:** 2026-04-13
**Referenced files last updated:** n/a
