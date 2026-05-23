# Track 02: Shell Navigation And Surface Model

## Goal

Replace the flat legacy rail as the top-level product model and surface the actual SplitShot modes.

## Required Top-Level Structure

- `Single Video`
- `Multi Video`
- `Performance Library`

## Required Shell Elements

- surface switcher
- context header
- active stage/workspace indicator
- return-to-workspace control
- render/proxy status visibility

## Required State Behaviors

- distinguish standalone stage vs workspace stage vs library browsing
- preserve correct context through route and pane changes
- expose loading, empty, stale, error, and unresolved-link states

## Acceptance

- the user always knows what surface they are in
- the shell no longer presents the legacy tool list as the product model
