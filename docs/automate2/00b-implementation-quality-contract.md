# Implementation Quality Contract

This document defines the quality standards for SplitShot v2 implementation.

## Code Quality

### Style

- Follow existing Python style (black-compatible)
- Follow existing JavaScript style (prettier-compatible)
- Use type hints in Python where practical
- Use JSDoc in JavaScript where practical

### Testing

- Every new feature must have unit tests
- Every new UI feature must have browser tests
- Every workflow must have an e2e test
- Coverage must not decrease

### Documentation

- Every public API must have docstrings
- Every UI feature must have a help tooltip
- Every complex workflow must have a user-facing explanation

## Performance

- UI interactions must respond within 100ms
- Library queries must complete within 500ms
- Analytics must render within 1 second
- Waveform must sustain 60fps
- Video preview must play smoothly

## Reliability

- No unhandled exceptions in production
- All file operations are atomic
- All pipelines are cancellable
- All async operations have timeouts

## Accessibility

- All interactive elements have aria-labels
- Color is not the only indicator of state
- Keyboard navigation works for all features
- Screen reader labels are meaningful

## Security

- No execution of user-provided commands
- All file paths are validated
- No network transmission of user content
- No sensitive data in logs

## Review Checklist

Before merging any change:

- [ ] Code follows style guide
- [ ] Tests pass
- [ ] Coverage maintained
- [ ] Documentation updated
- [ ] Performance acceptable
- [ ] Accessibility checked
- [ ] Security reviewed
- [ ] No forbidden names used

## Enforcement

- CI runs lint, format, and tests on every PR
- Code review required for all changes
- Performance benchmarks run on release candidates
- Accessibility audit run on UI changes
