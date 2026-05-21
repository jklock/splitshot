# SplitShot Product Definition v2

Audited against the current SplitShot repo, `docs/automate/`, `docs/automate-ui/`, and competitor screenshots on 2026-05-20.

## Summary

SplitShot is a **competition-shooting analysis-first editor and performance system** for **individual shooters**.

Core promise:

- **Truth**: derive, review, correct, and preserve authoritative run data.
- **Polish**: turn that reviewed truth into strong-looking exports.
- **Speed**: make common outcomes fast without reducing the product to a generic video maker.
- **Memory**: build a lasting record of every performance so shooters can learn from their own data over time.

## Target User

The primary user is an individual competition shooter who wants:

- detailed metrics on stage performance
- reliable timing and score truth
- the ability to show all meaningful data
- polished edited videos generated from that truth
- a long-term history of progress across runs, stages, and matches
- to quickly edit an entire match without repeating the same setup for every stage

## Product Surfaces

SplitShot has four top-level product surfaces:

1. `Landing Page` — the starting surface
2. `Stage Video Edit` — the focused stage editor
3. `Match Video Edit` — the match-level batch editor
4. `Performance Library` — the long-term performance record

### Landing Page

The Landing Page is the first thing a user sees when SplitShot opens.

Its job:

- greet the user with clear, friendly choices
- offer `Stage Video Edit`, `Match Video Edit`, and `Performance Library` as large, obvious entry points
- show recent activity (last opened stages, matches, library records) for fast return to work
- display quick-start shortcuts: "New Stage", "New Match", "Open Recent"
- never require the user to understand backend concepts like "projects" or "workspaces" to get started

Design rules:

- use plain English labels, not jargon
- each entry point must explain what it does in one sentence
- recent activity must be visually scannable (thumbnails, names, dates)
- the page must feel like a dashboard, not a file manager

### Stage Video Edit

Stage Video Edit is the focused one-stage editor.

Its job:

- import one run or stage video
- detect timer beep and shots
- let the user correct timing truth
- import official scoring context when available
- compute and display trustworthy metrics
- generate one or more output variants from that reviewed run
- provide all editing tools in one coherent view

This is the deep-dive surface. It must remain powerful and uncluttered.

### Match Video Edit

Match Video Edit is the match-level batch editor and manager.

Its job:

- manage many stage videos in one match workspace
- let the user configure settings on the **first stage** and apply them to **all remaining stages** automatically
- show a clear overview of all stages in the match
- indicate which stages are ready, which need review, and which are missing media
- allow quick per-stage overrides when needed
- let the user open any stage into Stage Video Edit for deep work and return seamlessly
- batch consistent exports across the match without flattening stage-specific truth
- build match-level outputs like recaps and montages

The key user promise is: **"Set it up once, apply to all, tweak if needed."**

### Performance Library

Performance Library is the separate long-term record and the app's killer feature.

Its job:

- mirror the latest reviewed truth from Stage Video Edit and Match Video Edit
- keep historical stage and match metrics available without reopening every old project manually
- store lightweight retained review-video proxies for recall and comparison
- store PracticeScore output and stage/match scoring data
- let the user move from history view back into the relevant editor scope
- provide analytics and insights: trends, comparisons, outliers
- answer questions like "How has my first-shot reaction improved over the last year?"

The Performance Library is not an afterthought. It is the reason a user keeps coming back to SplitShot.

## Product Rules

### Analysis-first

The editor is built around:

- imported official context
- measured timing truth
- computed metrics
- review and correction surfaces

Polished video is produced from that truth. Never the other way around.

### One truth, many outputs

For any stage:

- the reviewed run truth is authoritative
- multiple output variants can exist
- output variants may differ in layout, ratio, overlay density, watermark, title card, or subtitle preset
- output variants must not fork timing or scoring truth

### Setup once, apply everywhere

In Match Video Edit:

- the user configures output settings on the first stage
- SplitShot offers to apply those settings to all other stages in the match
- each stage can still be overridden individually
- the UI must make it obvious which stages are using shared settings vs. custom settings

### Same editor, two scopes

Stage Video Edit and Match Video Edit are not separate products.

They are two scopes over the same editing system:

- Stage Video Edit: one stage scope
- Match Video Edit: many-stage match scope

The user is changing focus, not changing tools.

### Separate but canonical library

Performance Library is separate from the editor workflow, but canonical over time.

It is not a full raw-media archive.
It is the durable record of:

- imported and derived metrics
- reviewed run identity
- PracticeScore output
- retained review proxies
- compressed video archives for long-term recall
- links back to editable stage or match workspaces

### Layman-friendly

Every feature must be explainable to someone who is not a video editor:

- use plain English labels (e.g., "Trim Dead Time" instead of "Run Window")
- provide sensible defaults for every setting
- show preview of changes before committing
- use visual feedback (thumbnails, waveforms, color coding) over text-heavy controls
- never require the user to understand ffmpeg, codecs, or container formats

## Non-goals

SplitShot is not:

- a social-first app
- a generic video editor
- an Apple-only product definition
- a coach or team platform first
- a cloud-first upload workflow
- a cinematic content studio that treats analysis as secondary
- a tool that requires the user to repeat the same configuration for every stage in a match

## Strategic Reframe vs Shooting Cut

SplitShot should borrow high-value workflows from Shooting Cut, but not its product identity.

SplitShot keeps:

- deeper timing review
- more explicit scoring and metrics truth
- match-scale historical performance analysis
- cross-platform desktop identity
- local-first storage

SplitShot adds:

- faster trim and output flows
- stronger multi-stage editing with "setup once, apply everywhere"
- more polished export recipes
- retained proxy recall in Performance Library
- **full-featured Performance Library with analytics and insights**
- **landing page for clear navigation**
- **layman-friendly UX throughout**

## Acceptance Criteria

- The product can be explained clearly through the four surfaces above.
- New features can be assigned cleanly to `Landing Page`, `Stage Video Edit`, `Match Video Edit`, or `Performance Library`.
- Future parity work must preserve analysis-first behavior and one-truth-many-outputs.
- A user can open SplitShot, see the Landing Page, and start editing a stage in under 30 seconds.
- A user can configure a match output recipe on stage 1 and apply it to all 8 stages without repeating work.
- A user can open Performance Library and compare their reload speed across the last 50 stages.

## Implementation Contract Additions

### Naming guardrail

Implementation work derived from this package must follow [00a-splitshot-naming-contract.md](00a-splitshot-naming-contract.md).

The product surfaces above remain stable. New capabilities under those surfaces must use SplitShot-native implementation labels rather than competitor labels.

### Current repo seams to extend

This package is grounded in the current live seams:

- `src/splitshot/domain/models.py`
  - `Project` is the current canonical editable truth object.
- `src/splitshot/persistence/projects.py`
  - save/load behavior centers on folder bundles containing `project.json`.
- `src/splitshot/ui/controller.py`
  - controller mutations, autosave, and app/folder/project settings layering are already established.
- `src/splitshot/browser/state.py`
  - browser state currently serializes one project into `/api/state`.
- `src/splitshot/browser/server.py`
  - the browser shell already exposes the existing `/api/*` control surface.
- `src/splitshot/browser/static/index.html`
  - the browser shell already has a surface switcher and automation panels.

### Product-level decisions locked by this package

- `Landing Page` is the authoritative starting surface.
- `Stage Video Edit` remains the authoritative editing surface for one stage record.
- `Match Video Edit` is a workspace layer over many stage records; it does not create a second truth model for stage analysis.
- `Performance Library` is a separate persisted history/index system layered beside project bundles, not inside them.
- Existing single-project workflows remain valid and must open without conversion prompts.
- All new output behavior must preserve one reviewed truth record with many output realizations.
- The "setup once, apply everywhere" workflow is a first-class product feature, not a convenience script.

### Implementation non-goals

- do not rename the four top-level surfaces
- do not replace the existing project model with unrelated parallel editor truth
- do not move saved single-stage projects into a mandatory match-only format
- do not make the library depend on cloud infrastructure
- do not copy Shooting Cut's UI layout or branding

### Package completion standard

Every remaining doc in this package must resolve:

- exact storage layout
- exact ids and relationships
- exact state and route contracts
- exact migration behavior
- exact proof expectations
- exact UI behavior and failure states

No later document in this package may defer those decisions with `TBD`, `later`, `should define`, or equivalent wording.
