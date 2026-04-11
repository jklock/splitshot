# Browser Compact Tool UI Final Audit

## Result

The browser cockpit now behaves more like a compact utility:

- Left rail reduced to 68px.
- Tool labels use `🍎` plus a single word.
- Duplicate startup copy was removed.
- Default status now starts as `Ready.`.
- `Open Stage Video` appears once in the toolbar.
- Empty state is reduced to `No video`.
- Typography uses Apple-style system fonts and a 13px base.
- Buttons, labels, metrics, split cards, inspector controls, waveform, and rail rows are reduced in scale.
- Existing review cockpit workflow remains intact.

## Validation

- `node --check src/splitshot/browser/static/app.js`
  - Result: passed
- `uv run pytest tests/test_browser_static_ui.py tests/test_browser_control.py tests/test_main_window.py`
  - Result: `13 passed`
- `uv run pytest`
  - Result: `42 passed`

## Notes

- This pass intentionally changed workflow density and copy, not backend behavior.
- Remaining UI refinement should be done against real screenshots after launch, focusing on direct manipulation and control grouping rather than adding explanation text.

