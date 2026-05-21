# Track 03: Match Video Editor UI

## Goal

Expose the workspace model as a real match-level editing surface, with the signature Setup Once, Apply Everywhere workflow.

## Required Workspace UI

### Workspace Header

- match name (editable)
- match date
- match-level scoring summary
- action buttons: Save, Export All, Build Recap

### Stage Grid

- table or card grid
- columns:
  - stage number
  - stage name (editable inline)
  - video thumbnail
  - status badge (missing, needs review, ready, custom)
  - settings badge (shared, custom, missing)
  - scoring summary
  - actions: Open, Override, Reset, Remove
- drag-and-drop reordering
- click to open stage

### Setup Once, Apply Everywhere Workflow

1. User configures Stage 1 in Stage Video Edit
2. User returns to match grid
3. If Stage 1 has configuration, show banner: "Stage 1 is configured. Apply to all other stages?"
4. User clicks "Preview Changes"
5. Show modal with:
   - list of stages that will be updated
   - which settings will change per stage
   - warning for stages with existing overrides
6. User clicks "Apply to All"
7. Apply settings, update grid
8. Show completion toast: "Applied to 7 stages"
9. Updated stages show "shared" badge

### Shared Defaults Panel

- editable defaults for the whole match
- shows which stages use defaults vs. overrides
- reset-all button

### Batch Export Panel

- select all / select none
- per-stage checkbox
- output recipe selector
- start export button
- export queue with progress bars
- cancel buttons
- completion summary

### Match Recap Builder

- stage inclusion/exclusion checkboxes
- stage order (drag to reorder)
- result-card configuration
- transition style selector
- preview before render button

### Stage Composite Builder

- clip list with thumbnails
- add/update/remove clip
- camera job assignment per clip
- line-up trigger/result state
- audio balance per clip
- override smart cuts list
- composite render action
- preview before render button

## Acceptance

- the workspace is no longer implicit or route-only
- stage grid is scannable and actionable
- drag-and-drop reordering works
- Setup Once, Apply Everywhere is smooth and clear
- batch export shows progress and completion
- Match Recap and Stage Composite remain separate flows in UI and proof
- the workflow feels magical, not mechanical
