# SplitShot Documentation

Start with the product guides, then use the maintainer material only when you are working on the repository.

## Product Guides

- [User guide](userfacing/USER_GUIDE.md)
- [Workflow](userfacing/workflow.md)
- [Troubleshooting](userfacing/troubleshooting.md)
- [Pane guides](userfacing/panes/)

The screenshot set in [screenshots/](screenshots/) documents every left-rail pane, expanded workspace, shared modal, and each Settings section. Regenerate it with two approved real recordings:

```bash
uv run python scripts/docs/capture_browser_screenshots.py \
  --primary-video tests/video/Stage3.MP4 \
  --secondary-video tests/video/Stage3-double.MP4
```

The capture validates decoded non-black video frames and the configured showcase state before writing 1400x900 images. Review the generated contact sheet in `tmp/codex/doc-screenshots/contact-sheet.png` before committing the set.

## Maintainer Guides

- [Development](project/DEVELOPING.md)
- [Architecture](project/ARCHITECTURE.md)
- [Release validation](project/ELECTRON_RELEASE.md)
- [Governance](project/GOVERNANCE.md)
- [Limitations](project/LIMITATIONS.md)
- [Test suite guide](tests/TEST_SUITE_GUIDE.md)
- [Script catalog](../scripts/README.md)
- [Contributing](../CONTRIBUTING.md)

## Technical References

- [ShotML behavior](analysis/SHOTML.md)
- [ShotML architecture](project/SHOTML_ARCHITECTURE.md)
- [Browser pane ownership](project/browser-pane-ownership.md)
- [Browser control test matrix](project/browser-control-qa-matrix.md)
- [Source tree map](../src/splitshot/README.md)
