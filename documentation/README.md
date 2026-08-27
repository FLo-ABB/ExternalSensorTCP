# ExternalSensorTCP documentation

This folder contains the user-facing documentation for the TCP-based External Sensor integration used by PickMaster Twin/Lite.

## Overview

`ExternalSensorTCP` connects to a TCP position sensor, receives text-based acquisition and object data, and forwards valid positions to PMTW for robot coordination. The implementation supports a single sensor instance and works with a TCP server that sends acquisition triggers and object blocks in a predictable format.

## Documentation map

- [Installation](installation.md) — required setup and deployment steps
- [Configuration](configuration.md) — sensor, logger, and position-generator setup
- [Protocol](protocol.md) — TCP text message format and position payload sent to PMTW
- [Architecture](architecture.md) — project structure, runtime flow, shutdown behavior, extending
- [Logging](logging.md) — default log behavior, rotation, and sample output
- [Troubleshooting](troubleshooting.md) — common issues, fixes, and error reference

## Main runtime flow

```text
PMTW
  └─ ExternalSensorTCP
       ├─ configureSensor()
       ├─ configurePosGen()
       └─ startSensor()
            └─ SensorFunctions.startSensor()
                 ├─ connect to TCP sensor
                 ├─ parse trigger and position lines
                 ├─ match AcqNo to strobe time
                 └─ call callback.NewPosition(objects)
```

See [Architecture](architecture.md) for full details.

## Files in this project

- `ExternalSensorTCP.py` — main runtime class and lifecycle logic
- `SensorFunctions.py` — TCP receive loop and position parsing
- `SensorUI.py` — configuration dialogs
- `SensorLogger.py` — bounded file logger and rotation logic
- `ExternalSensorInterface.py` — ABB interface contract

## Default behavior

- Logging is disabled by default.
- The default file name is `ExternalSensor.log`.
- The logger rotates at 50 MB.
- Only the 5 most recent rotated files are retained.
- A warning is emitted once when the file is rotated.

## License

This project is released under the MIT License. See the repository root `LICENSE` file for the full text.
