# Browser Layout Popout QA Final Audit

## Implemented

| Area | Result |
| --- | --- |
| Logo | The left rail brand cell is larger and the packaged logo scales inside the clipped cell. |
| Top metrics strip | Metrics now use fixed cells sized from the inspector width, so the right-side metric boxes align with the sidebar below. |
| Filename display | Browser file-picker imports preserve original display names while keeping safe temp media paths internally. UUID temp prefixes are no longer shown to users. |
| Right inspector stability | The inspector has a fixed width, hidden horizontal overflow, and ellipsis handling for dense detail rows and tables. |
| Waveform popout | Waveform expansion now hides the video and inspector so the waveform becomes the main workspace, with a larger waveform area and visible shot list. |
| Button logging | All button clicks are captured globally and written to the browser activity log with button identity and behavior metadata. |
| Control logging | Input, select, textarea, and file selection changes are captured globally and written to the browser activity log. |
| Button QA | A button matrix documents each control, expected app effect, and expected log evidence. |

## Validation

| Check | Result |
| --- | --- |
| JavaScript syntax | `node --check src/splitshot/browser/static/app.js` passed. |
| Targeted browser tests | `uv run --python 3.12 pytest tests/test_browser_static_ui.py tests/test_browser_control.py` passed with 16 tests. |
| Full suite | `uv run --python 3.12 pytest` passed with 47 tests. |
| Runtime check | `uv run --python 3.12 splitshot --check` found `ffmpeg`, `ffprobe`, and browser static assets. |
| Button activity smoke | Browser server smoke run logged 40 `button.click` records for the current button inventory. |

## Log Review

| Log file | Finding |
| --- | --- |
| `logs/splitshot-browser-20260411-154640-686214a4.log` | Pre-change log showed UUID-prefixed temp filenames, partial button logging, and waveform activity behaving like compact seek/edit events. |
| `logs/splitshot-browser-20260411-160718-bf2b71d3.log` | Post-change smoke log shows every static browser button emits `browser.activity` with `button.click` detail. |
| Full test run logs | API route logs show project import, primary and secondary file imports, overlay/scoring calls, sync, swap, and expected shutdown events. |

## Residual Risk

The repository still validates browser UI behavior primarily through static DOM/CSS contracts, server API tests, and activity smoke logs. A real browser automation stack is not currently installed, so pointer drag behavior is covered by event wiring, API effects, and manual browser testing rather than rendered end-to-end Playwright-style tests.
