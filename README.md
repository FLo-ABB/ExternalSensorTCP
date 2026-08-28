# ExternalSensorTCP

A lightweight Python integration for the PickMaster Twin/Lite External Sensor interface. It connects to a TCP-based position sensor, parses acquisition and object data from the incoming text stream, and forwards valid positions to PMTW for robot pick-and-place coordination.

**Author:** F. LOBERT, ABB  
**Status:** Working  
**License:** MIT

> This project is provided as-is with no formal support. Issues and pull requests are welcome for bug fixes and improvements.

## Features

- TCP client connection to an external sensor server
- Acquisition trigger and object parsing for PMTW-compatible position messages
- Configurable sensor IP, port, and logger settings
- Safe bounded logging with automatic rotation at 50 MB
- Single-sensor runtime model aligned with the ABB interface contract

## Quick start

1. Copy `scripts\ExternalSensorTCP.py`, `scripts\ExternalSensorInterface.py`, `scripts\SensorFunctions.py`, `scripts\SensorLogger.py`, and `scripts\SensorUI.py` into the PickMaster scripts folder `%PROGRAMDATA%\ABB\PickMaster\PMScripts\`.
2. In PickMaster, add an **External Sensor** and enter `ExternalSensorTCP.py` as the script name.
3. Configure the sensor's TCP IP/port and (optionally) logging.

See the [documentation](documentation/README.md) for full setup, configuration, protocol, and troubleshooting details.

## Documentation

- [Documentation index](documentation/README.md)
- [Installation](documentation/installation.md)
- [Configuration](documentation/configuration.md)
- [Protocol](documentation/protocol.md)
- [Architecture](documentation/architecture.md)
- [Logging](documentation/logging.md)
- [Troubleshooting](documentation/troubleshooting.md)

## Examples

Example configurations and integration guides for common sensor types:

- **`example/cognex/`** — Cognex job file
- **`example/keyence/`** — Keyence programs (calibration and ShapeTrax3A)

## Releases

Packaged releases are published from GitHub. Each release contains a ZIP archive of the `scripts/` folder named `ExternalSensorTCP-X.Y.zip`.

The version number is **not** entered by hand: it is read from the `version` attribute of the `ExternalSensorTCP` class in [`scripts/ExternalSensorTCP.py`](scripts/ExternalSensorTCP.py) — the same value that PickMaster shows as Sensor Information.

- `X` (major): new functions / features
- `Y` (minor): bug fixes

To publish: bump `version` in `scripts/ExternalSensorTCP.py` through a pull request, then run the **Release** workflow from the *Actions* tab (`Run workflow`). It lints, runs the tests, builds the archive and creates the `vX.Y` tag and GitHub release. The run fails if the tag already exists, so the version must be bumped before each release.

## Contributing

We welcome improvements, bug reports, and feature requests.

1. Open an issue before starting major work if you want to discuss a change or feature.
2. Create a dedicated branch for your fix or feature
3. Keep changes focused and update the documentation when behavior changes.
4. Open a pull request with a short summary, motivation, and validation notes.

Direct pushes to `main` are not allowed. Every change must go through a pull request whose CI checks (lint, tests, version format) pass before merging.

> Please do not open a pull request without a related issue or a clear change description.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
