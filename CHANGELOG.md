# Changelog

All notable changes to ExternalSensorTCP are documented in this file.

The version number is the `version` attribute of the `ExternalSensorTCP` class in
`scripts/ExternalSensorTCP.py` (shown as Sensor Information in PickMaster):

- `X` (major): new functions / features
- `Y` (minor): bug fixes

Only changes that affect the script package shipped in the release ZIP should
bump this version. Documentation-only, CI-only, and repository metadata changes
do not require a new version.

Add a `## X.Y` section here in the same pull request that bumps the version. The
Release workflow extracts that section into the release notes shipped next to the
ZIP archive.

## 1.2

### Changed

- Simplified logging configuration: select whether logging is enabled and its
  folder; log files are always named `ExternalSensor.log`.
- Changed the default log folder to the installed PickMaster scripts folder.
- Replaced the legacy raw-position `SensorLog.txt` output with the configurable
  `ExternalSensor.log` logger.
- Stored logger settings in `ExternalSensorTCP.config.json` beside the installed
  scripts. Reconfigure logging after upgrading because settings stored in the
  former `C:\PMScriptsConfig` location are not migrated.
- Limited log rotation to the files created by this logger, preventing unrelated
  files with similar names from being removed.

## 1.1

### Changed

- Log rotation no longer writes warning messages to the error output.
- Release packages now include the MIT license and a link to the source
  repository.

## 1.0

### Added

- TCP client connection to an external sensor server.
- Acquisition trigger and object parsing for PMTW-compatible position messages.
- Configurable sensor IP, port, and logger settings.
- Bounded logging with automatic rotation at 50 MB.
- Single-sensor runtime model aligned with the ABB interface contract.
