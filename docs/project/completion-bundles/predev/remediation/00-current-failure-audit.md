# Current Failure Audit

## Root Failure

The broken UI came from mixing four incompatible navigation models into one browser shell:

- shell-level Stage / Match / Library tabs
- hidden surface header tabs and home controls
- legacy Stage tool rail
- Match / Library automation panels mounted like Stage subpanels

That made the app look unstable because ownership was unstable.

## Fixed In This Pass

- removed the visible shell-level workspace tab bar
- removed the Stage-top automation strip and hidden surface header path
- restored Stage to the existing editor shell instead of a stacked cockpit
- rebuilt Match Video Edit as a sidebar + workspace view
- rebuilt Performance Library as a sidebar + workspace view
- added visible `Home` controls to all three work views
- added Match- and Library-local settings sections
- moved Match and Library rendering out of root `app.js`

## Remaining Risk

- Stage still keeps its historical right-side project/import-heavy inspector content, so visual polish there is restored structurally but not yet reworked feature by feature.
- The archived automate plans still contain stale claims; only copied-forward docs should be treated as active.
