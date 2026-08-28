# Changelog

All notable changes to ExternalSensorTCP are documented in this file.

The version number is the `version` attribute of the `ExternalSensorTCP` class in
`scripts/ExternalSensorTCP.py` (shown as Sensor Information in PickMaster):

- `X` (major): new functions / features
- `Y` (minor): bug fixes

Add a `## X.Y` section here in the same pull request that bumps the version. The
Release workflow extracts that section into the release notes shipped next to the
ZIP archive.

## 1.0

### Added

- TCP client connection to an external sensor server.
- Acquisition trigger and object parsing for PMTW-compatible position messages.
- Configurable sensor IP, port, and logger settings.
- Bounded logging with automatic rotation at 50 MB.
- Single-sensor runtime model aligned with the ABB interface contract.
