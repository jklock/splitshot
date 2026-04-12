# Browser Waterfall Workflow Repair Gap Analysis

## Pessimistic Findings

- Static tests over-counted as confidence. They verified markup strings and event names, but did not prove secondary video preview, overlay color output, status visibility, or export artifacts were actually visible.
- API tests confirmed server mutations, but the browser UI could still hide or misplace the effect. Secondary import was a clear example: the project state had a secondary video, but the page never rendered it in the video box.
- The inspector became a dumping ground. Split cards, selected-shot controls, scoring, overlay, layout, and export all competed for the same sidebar without page-specific ownership.
- Expanded modes were global CSS flags. Once enabled, they survived navigation and made unrelated pages look broken.
- Overlay and score had two rendering models. Browser preview and FFmpeg export shared concepts, but scoring still created large transient letters even after the product requirement changed to “score text inside shot badge.”
- The status bar was implemented as a fixed grid row and then hidden with visibility/opacity, so it still stole space even when it was not semantically visible.
- Merge export was tested, but merge preview was not. Users judge WYSIWYG behavior in the video box before export, so this must be tested as markup/wiring plus API output.

## Remediation

- Add state-model tests for every new overlay setting so persistence and API state cannot silently drop fields.
- Add static UI tests for secondary video element, merge-preview CSS, renamed rail/page labels, destructive project button, status-bar hidden behavior, waveform zoom controls, and review/layout ownership.
- Add renderer tests that inspect exported pixels/text behavior through MP4 output where possible.
- Keep button tests strict: every `<button>` needs a wired ID or behavior attribute, and each wired ID must have an event listener.
- Treat browser logs as a regression signal: every button click is logged; tests now validate the logger exists, while manual QA can use run logs to trace broken actions.

## Remaining Risk

- Full browser automation is still limited because the current test stack does not include Playwright/Selenium. The repair pass compensates with server API tests, static wiring assertions, export artifact tests, and generated Stage1 output.
- Pixel-level validation proves overlay paint exists, but not every visual preference. Visual QA remains necessary for exact layout preference.

