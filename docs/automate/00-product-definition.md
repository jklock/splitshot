# SplitShot Product Definition

Audited and drafted against the current SplitShot repo and [shootingcut.com](https://shootingcut.com) on 2026-05-18.

## Summary

SplitShot is a **competition-shooting analysis-first editor and performance system** for **individual shooters**.

Core promise:

- **Truth**: derive, review, correct, and preserve authoritative run data.
- **Polish**: turn that reviewed truth into strong-looking exports.
- **Speed**: make common outcomes fast without reducing the product to a generic video maker.

Top-level product surfaces:

1. `Single Video`
2. `Multi Video`
3. `Performance Library`

## Target User

The primary user is an individual competition shooter who wants:

- detailed metrics on stage performance
- reliable timing and score truth
- the ability to show all meaningful data
- polished edited videos generated from that truth
- a long-term history of progress across runs, stages, and matches

## Product Definition

### Single Video

Single Video is the focused stage editor.

Its job:

- import one run or stage video
- detect timer beep and shots
- let the user correct timing truth
- import official scoring context when available
- compute and display trustworthy metrics
- generate one or more output variants from that reviewed run

### Multi Video

Multi Video is the match-level editor.

Its job:

- manage many stage videos in one match workspace
- apply shared settings across the match by default
- allow stage-local overrides when needed
- let the user open a stage into the focused Single Video scope and return seamlessly
- batch consistent exports across the match without flattening stage-specific truth

### Performance Library

Performance Library is the separate long-term record.

Its job:

- mirror the latest reviewed truth from SplitShot workspaces
- keep historical stage and match metrics available without reopening every old project manually
- store lightweight retained review-video proxies for recall and comparison
- let the user move from history view back into the relevant editor scope

## Product Rules

### Analysis-first

The editor is built around:

- imported official context
- measured timing truth
- computed metrics
- review and correction surfaces

Polished video is produced from that truth.

### One truth, many outputs

For any stage:

- the reviewed run truth is authoritative
- multiple output variants can exist
- output variants may differ in layout, ratio, overlay density, watermark, title card, or subtitle preset
- output variants must not fork timing or scoring truth

### Same editor, two scopes

Single Video and Multi Video are not separate products.

They are two scopes over the same editing system:

- Single Video: one stage scope
- Multi Video: many-stage match scope

The user is changing focus, not changing tools.

### Separate but canonical library

Performance Library is separate from the editor workflow, but canonical over time.

It is not a full raw-media archive.
It is the durable record of:

- imported and derived metrics
- reviewed run identity
- retained review proxies
- links back to editable stage or match workspaces

## Non-goals

SplitShot is not:

- a social-first app
- a generic video editor
- an Apple-only product definition
- a coach or team platform first
- a cloud-first upload workflow
- a cinematic content studio that treats analysis as secondary

## Strategic Reframe vs Shooting Cut

SplitShot should borrow high-value workflows from Shooting Cut, but not its product identity.

SplitShot keeps:

- deeper timing review
- more explicit scoring and metrics truth
- match-scale historical performance analysis
- cross-platform desktop identity

SplitShot adds:

- faster trim and output flows
- stronger multi-stage editing
- more polished export recipes
- retained proxy recall in Performance Library

## Acceptance Criteria

- The product can be explained clearly through the three surfaces above.
- New features can be assigned cleanly to `Single Video`, `Multi Video`, or `Performance Library`.
- Future parity work must preserve analysis-first behavior and one-truth-many-outputs.

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

### Product-level decisions locked by this package

- `Single Video` remains the authoritative editing surface for one stage record.
- `Multi Video` is a workspace layer over many stage records; it does not create a second truth model for stage analysis.
- `Performance Library` is a separate persisted history/index system layered beside project bundles, not inside them.
- Existing single-project workflows remain valid and must open without conversion prompts.
- All new output behavior must preserve one reviewed truth record with many output realizations.

### Implementation non-goals

- do not rename the three top-level surfaces
- do not replace the existing project model with unrelated parallel editor truth
- do not move saved single-stage projects into a mandatory match-only format
- do not make the library depend on cloud infrastructure

### Package completion standard

Every remaining doc in this package must resolve:

- exact storage layout
- exact ids and relationships
- exact state and route contracts
- exact migration behavior
- exact proof expectations

No later document in this package may defer those decisions with `TBD`, `later`, `should define`, or equivalent wording.
