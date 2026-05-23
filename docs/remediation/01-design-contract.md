# Design Contract

## Shell

- The shell owns branding and processing status only.
- The shell must not own Stage / Match / Library product navigation.

## Stage Video Edit

- Keep the legacy left rail as the primary sidebar.
- Keep the preview, timeline, and inspector structure intact.
- Do not reintroduce a top automation strip.
- Sidebar footer order: `Home`, then `Settings`.

## Match Video Edit

- Use the same overall grammar as Stage:
  - persistent left sidebar
  - large main content area
  - workspace-owned actions
- Sidebar footer order: `Home`, then `Settings`.

## Performance Library

- Use the same overall grammar as Match:
  - persistent left sidebar
  - large main content area
  - workspace-owned actions
- Sidebar footer order: `Home`, then `Settings`.

## Completion Gate

- A surface is only considered fixed when the screenshot shows the correct navigation model and no duplicated shell bars.
