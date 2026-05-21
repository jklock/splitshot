# Release Readiness

This document defines the release readiness criteria for SplitShot v2.

## Version

Target version: `v2.0.0`

## Release Checklist

### Code

- [ ] All features implemented
- [ ] All tests passing
- [ ] No P0 or P1 bugs open
- [ ] Code review complete
- [ ] Lint and format checks pass

### Documentation

- [ ] User guide updated
- [ ] Troubleshooting guide updated
- [ ] README updated
- [ ] AGENTS.md updated
- [ ] CHANGELOG.md updated

### Data

- [ ] Data model migration tested
- [ ] Legacy project compatibility verified
- [ ] Library index rebuild tested
- [ ] Backup/restore tested

### Performance

- [ ] Library query benchmark <500ms
- [ ] Analytics render benchmark <1s
- [ ] Waveform render benchmark 60fps
- [ ] Export throughput benchmark acceptable

### Packaging

- [ ] Electron build passes
- [ ] Windows installer tested
- [ ] macOS bundle tested
- [ ] Linux AppImage tested

### Release Assets

- [ ] Release notes written
- [ ] Version bumped in all files
- [ ] Tag created
- [ ] GitHub release drafted

## Post-Release

- [ ] Monitor error reports
- [ ] Respond to user feedback
- [ ] Plan first patch release

## Rollback Plan

If critical issues are found:

1. Mark release as pre-release on GitHub
2. Publish hotfix branch
3. Fix issues
4. Release `v2.0.1`
5. Do not delete `v2.0.0` tag
