# Repository instructions

## Versioning and release notes

- The source of truth for the package version is `scripts/ExternalSensorTCP.py`.
  The `version` attribute of `ExternalSensorTCP` is the value used for release
  packaging and GitHub tags.
- `CHANGELOG.md` is for script users only. It documents user-visible changes in
  the packaged script ZIP, not repository maintenance, CI, documentation, or
  process-only changes.
- Add a matching `## X.Y` section in `CHANGELOG.md` in the same pull request that
  bumps the version. The release workflow extracts that section into the published
  release notes.
- Keep the README version-free. The version number should appear only once in the
  code base, in the script implementation, so documentation stays maintainable.

## Tests

- Precede every test with a concise comment that states what it verifies and
  the expected result.
- Keep comments inside tests only when they clarify non-obvious setup or an
  assertion that would otherwise be difficult to understand.
