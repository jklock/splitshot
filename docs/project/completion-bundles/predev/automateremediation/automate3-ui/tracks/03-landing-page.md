> **Note:** Track status is partial. See `../todo.md` for live checklist.


# Track 03: Landing Page

## Goal

Create a professional front door for first-run and returning users.

## Required UI

- SplitShot identity and concise value copy
- Stage Video Edit card
- Match Video Edit card
- Performance Library card
- recent activity
- New Stage
- New Match
- Open File
- version/help/settings access
- empty recent state
- responsive layout.

Current limitation: `/api/landing/recent` returns only stage project directories from `~/.splitshot/projects`. It does not return Match or Library records. The UI must display returned records honestly and must not fabricate Match/Library recent items.

## Behaviors

- cards open the correct view
- quick starts create or open the correct context
- recent items reopen Stage/Match/Library targets
- failed reopen shows a clear unavailable state.

## Proof

- empty/first-run screenshot
- returning-user screenshot with recent items
- browser test for card navigation
- route/API test for recent activity payload.
