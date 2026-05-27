# Track 01: Landing Page And Shell Navigation

## Goal

Create a clear, friendly landing page and replace the flat legacy rail with the four-surface model.

## Required Top-Level Structure

- `Landing Page`
- `Stage Video Edit`
- `Match Video Edit`
- `Performance Library`

## Landing Page Requirements

### Layout

- full-screen page, not a modal
- dark theme consistent with SplitShot
- hero section with SplitShot logo and tagline
- three large entry cards in a row
- recent activity section below
- footer with version and links

### Entry Cards

Each card must have:
- large icon
- title (plain English)
- one-sentence description
- hover state
- click opens the surface

Cards:
1. **Stage Video Edit** — "Review and polish one stage at a time"
2. **Match Video Edit** — "Edit a whole match quickly"
3. **Performance Library** — "See your progress over time"

### Recent Activity

- show last 5-10 opened items
- each item: thumbnail, name, date, type (stage/match)
- click opens the item directly
- empty state: "No recent activity. Start by editing a stage!"

### Quick-Start Shortcuts

- "New Stage" button
- "New Match" button
- "Open File" button (opens existing project)

### Empty State

- friendly illustration or icon
- "Welcome to SplitShot!"
- getting-started tips
- link to user guide

## Shell Requirements

### Top-Level Navigation

- surface switcher in the header
- active surface highlighted
- "Home" button returns to Landing Page
- SplitShot logo returns to Landing Page

### Context Header

- active project or workspace name
- active stage name when relevant
- editing mode indicator
- return-to-workspace button when applicable

### Mode Awareness

- tool panes change based on active surface
- `Stage Video Edit` shows all editing panes
- `Match Video Edit` shows workspace panes
- `Performance Library` shows library panes
- `Landing Page` shows no panes

## Required State Behaviors

- distinguish standalone stage vs workspace stage vs library browsing vs landing
- preserve correct context through route and pane changes
- expose loading, empty, stale, error, and unresolved-link states
- recent activity updates when projects are opened or saved

## Acceptance

- the user always knows what surface they are in
- the shell no longer presents the legacy tool list as the product model
- the landing page loads in under 1 second
- recent activity is accurate and up-to-date
- empty state is friendly and helpful
- all entry points work
