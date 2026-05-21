# Automate3

Automate3 is the end-to-end remediation package for the final SplitShot product UI. It supersedes the incomplete direction in `docs/automate/`, `docs/automate2/`, `docs/automate-ui/`, and `docs/automate2-ui/` without deleting those packages.

Automate3 starts from the 2026-05-21 visual audit: the current app has useful backend and editor pieces, but the browser UI still reads as one legacy cockpit with conditional panels bolted onto it. The final product must be a professional, integrated, local-first video analysis editor with four frontend views:

1. [Landing Page](../automate3-ui/tracks/03-landing-page.md)
2. [Stage Video Edit](03-stage-video-edit-spec.md)
3. [Match Video Edit](04-match-video-edit-spec.md)
4. [Performance Library](05-performance-library-spec.md)

## Read Order

1. [MASTER.md](MASTER.md)
2. [00-product-definition.md](00-product-definition.md)
3. [00a-splitshot-naming-contract.md](00a-splitshot-naming-contract.md)
4. [00b-implementation-quality-contract.md](00b-implementation-quality-contract.md)
5. [01-current-state-audit.md](01-current-state-audit.md)
6. [02-end-to-end-workflow-spec.md](02-end-to-end-workflow-spec.md)
7. [03-stage-video-edit-spec.md](03-stage-video-edit-spec.md)
8. [04-match-video-edit-spec.md](04-match-video-edit-spec.md)
9. [05-performance-library-spec.md](05-performance-library-spec.md)
10. [06-data-model-and-state-contract.md](06-data-model-and-state-contract.md)
11. [07-api-and-backend-contract.md](07-api-and-backend-contract.md)
12. [08-technical-architecture.md](08-technical-architecture.md)
13. [09-implementation-roadmap.md](09-implementation-roadmap.md)
14. [10-acceptance-and-proof.md](10-acceptance-and-proof.md)
15. [11-release-readiness.md](11-release-readiness.md)
16. [12-subagent-orchestration-prompt.md](12-subagent-orchestration-prompt.md)
17. [13-remediation-and-completion-plan.md](13-remediation-and-completion-plan.md)
18. [14-truth-audit-matrix.md](14-truth-audit-matrix.md)
19. [15-pre-implementation-review.md](15-pre-implementation-review.md)
20. [16-second-pass-audit.md](16-second-pass-audit.md)

The browser-shell implementation command center is [../automate3-ui/README.md](../automate3-ui/README.md).

## Implementation Documents

For the exhaustive build specification, see:
- [../automate3-ui/artifacts/implementation-guide.md](../automate3-ui/artifacts/implementation-guide.md) — master implementation document
- [../automate3-ui/artifacts/css-class-spec.md](../automate3-ui/artifacts/css-class-spec.md) — exact CSS classes
- [../automate3-ui/artifacts/js-module-spec.md](../automate3-ui/artifacts/js-module-spec.md) — exact JavaScript functions
- [../automate3-ui/artifacts/commit-plan.md](../automate3-ui/artifacts/commit-plan.md) — commit-by-commit migration

## Completion Meaning

This package is planning truth only. The current implementation is not complete. The future implementation is complete only when it is fully functional, tested, visually proven with empty and loaded screenshots, documented, and ready for users.
