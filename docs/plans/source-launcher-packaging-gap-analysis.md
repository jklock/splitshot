# Source Launcher Packaging Gap Analysis

## Current State

- `splitshot` launches the desktop UI.
- `splitshot-web` launches the browser UI.
- Browser mode exists and is tested, but it is not the default entry point.
- README currently documents both modes but still presents desktop first.
- Toolchain validation exists as a script, not as part of the main command.

## Gaps

1. Primary command does not match desired product direction.
   - Closure: Change `splitshot` to launch browser mode by default.

2. Desktop launch is not clearly secondary.
   - Closure: Add `splitshot --desktop` and document it as the secondary mode.

3. Users need a simple health check.
   - Closure: Add `splitshot --check` that validates FFmpeg/FFprobe and static browser assets.

4. Compatibility commands should not break.
   - Closure: Keep `splitshot-web`; add `splitshot-desktop` for direct desktop launch.

5. Launch behavior needs feature tests.
   - Closure: Add tests for CLI parser/help, check command, and mode dispatch without starting long-running servers.
