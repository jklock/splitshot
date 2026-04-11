# Browser Server Terminal Hygiene Gap Analysis

## Gaps

- `BrowserControlServer.serve_forever` does not catch `KeyboardInterrupt`.
- `_send_media` writes chunks without treating client disconnects as normal browser behavior.
- `ThreadingHTTPServer` uses default `handle_error`, so any uncaught client disconnect can print traceback noise.
- Tests do not cover interrupted foreground serving or media-stream disconnects.

## Fixes

- Add a server subclass that suppresses expected disconnect exceptions.
- Catch `KeyboardInterrupt` in foreground serving and return cleanly.
- Catch disconnect errors during media chunk writes and end that response quietly.
- Add focused tests around both paths.

