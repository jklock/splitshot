# Match Video Edit Spec

Match Video Edit is the workspace-level frontend. It must not be a configuration panel inside the Stage editor.

## Required Layout

Match Video Edit must have:

- match header with editable name/date and save/export actions
- match status summary
- stage grid or table
- shared defaults panel
- stage override panel
- Setup Once Apply Everywhere workflow
- Match Recap builder
- Stage Composite builder
- batch export queue
- PractiScore import/status area
- professional empty state for no match/no stages.

## Stage Grid

Each stage row/card must show:

- stage number
- stage name
- thumbnail when available
- media status
- review status
- scoring summary
- shared/custom/missing settings badge
- last reviewed/exported indicator when available
- actions: Open, Override, Reset, Remove
- drag handle for reordering.

## Setup Once Apply Everywhere

Required flow:

1. detect reusable Stage 1 configuration
2. show a clear prompt in Match
3. preview changes before applying
4. list affected stages and conflicts
5. confirm apply
6. update grid and badges
7. allow reset/override per stage.

Backend gap: the current `/api/workspace/apply-from-first` and `/api/workspace/apply-from-first/preview` routes are metadata-oriented. They do not yet diff or copy actual project settings such as output profiles, overlay visibility, or export settings from Stage 1's project to sibling stages. A complete implementation requires:

1. diffing the actual Stage 1 `Project` state against each sibling stage
2. generating a preview of concrete changes, for example `Stage 3 will inherit Video Shape: 16:9`
3. detecting conflicts where a sibling has explicit overrides
4. applying changes to sibling stage projects and persisting them

The UI must not claim Setup Once Apply Everywhere is complete until backend tests prove these behaviors.

## Match Recap

Required:

- stage inclusion/exclusion
- order control
- result-card settings
- transition/style options
- preview before render
- render action and progress.

## Stage Composite

Required:

- clip list with thumbnails
- add/update/remove clip
- camera job assignment
- line-up result state
- audio balance
- override smart cuts
- preview before render
- render action and progress.

## Acceptance

Match is acceptable only when:

- a user can manage the match without opening hidden route panels
- Stage opens and returns cleanly
- shared defaults and overrides are understandable
- Setup Once Apply Everywhere is previewed and reversible enough for real work
- batch export and recap/composite workflows show progress and completion.
