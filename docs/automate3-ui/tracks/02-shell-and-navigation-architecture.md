# Track 02: Shell And Navigation Architecture

## Goal

Replace the one-cockpit model with a shared shell and four separate view bodies.

## Required Shell

- logo/home action
- active view switcher
- global context header
- project/match/stage status
- return-to-match affordance when relevant
- settings/help access
- notification/status area.

## View Switching

- Landing to Stage/Match/Library is direct.
- Stage can attach/create Match without forced navigation.
- Match can open Stage and return.
- Library can reopen Stage/Match intentionally.
- View local state is preserved where useful.

## View Transition Behavior

- Views switch instantly (no animated transition) to keep the app responsive.
- When leaving Stage, pause primary and secondary video playback to avoid audio continuing in the background.
- When returning to Stage, restore the last active tool pane and playback position if available.
- Match grid scroll position and selected stage must survive a round-trip through Stage and back.
- Library filters and selected record must survive a round-trip through Stage/Match and back.
- Export progress (if running) must remain visible in the shell status area regardless of active view.

## Retire Legacy Rail As Product Navigation

The legacy Stage tool list may remain inside Stage Video Edit. It must not be presented as the top-level product model for Match or Library.

## Acceptance

- Match and Library mount without irrelevant Stage chrome.
- Landing shows no editor panes.
- Stage panes remain available inside Stage.
- tests prove view switching and context retention.
