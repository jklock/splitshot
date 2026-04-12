# Browser Overlay and Score Cleanup Gap Analysis

## Why The Previous Pass Failed

- The implementation added configuration fields but did not verify the visual outcome. This allowed overlay containers to stretch full-height and turn badge settings into giant bars.
- The scoring UI technically had a select, but it was below other content and not tied visually to each shot row. That fails the actual workflow.
- The split-card grid survived even after the user asked for it to be removed. Keeping it added clutter and contradicted the workflow.
- Layout tests still asserted old elements instead of asserting their absence and functional replacements.
- Static wiring tests were not enough. They need to validate that removed controls are gone and directly editable controls are present where the user sees them.
- Stage1 export exposed a real pipeline defect: the encoder finished and wrote the MP4, but the decoder process reported `Broken pipe` after the pipe closed, causing SplitShot to surface a false export failure.

## Remediation

- Remove non-essential UI instead of hiding it under new pages.
- Make each visible score row perform its own assignment.
- Make overlay position calculations own all placement, with CSS only defining visual style.
- Add tests that explicitly fail if split cards, behavior copy, or score-position controls return.
- Add a test for the expected FFmpeg decoder pipe shutdown path.
- Generate a new Stage1 preview after fixes to inspect overlay size and placement.
