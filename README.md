# ExternalSensorTCP

A lightweight Python integration for the PickMaster Twin/Lite External Sensor interface. It connects to a TCP-based position sensor, parses acquisition and object data from the incoming text stream, and forwards valid positions to PMTW for robot pick-and-place coordination.

**Author:** F. LOBERT, ABB  
**Version:** 1.0  
**Status:** Working  
**License:** MIT

> This project is provided as-is with no formal support. Issues and pull requests are welcome for bug fixes and improvements.

## Documentation

- [Documentation index](documentation/README.md)
- [Installation](documentation/installation.md)
- [Configuration](documentation/configuration.md)
- [Logging](documentation/logging.md)
- [Troubleshooting](documentation/troubleshooting.md)

---

## Overview

This integration is intended for machine-vision or positioning sensors that expose a TCP text stream. The runtime matches each position message to its acquisition trigger, filters empty object slots, and sends only valid detections to PMTW.

---

## Features

- TCP client connection to an external sensor server
- Acquisition trigger and object parsing for PMTW-compatible position messages
- Configurable sensor IP, port, and logger settings
- Safe bounded logging with automatic rotation at 50 MB
- Single-sensor runtime model aligned with the ABB interface contract

---

## Prerequisites

- PickMaster Twin/Lite with External Sensor support
- Python 3.10+
- The project files deployed to `%PROGRAMDATA%\ABB\PickMaster\PMScripts\`

---

## Project structure

| File                         | Role                                                                             |
| ---------------------------- | -------------------------------------------------------------------------------- |
| `ExternalSensorTCP.py`       | Main runtime — orchestrates configuration, thread lifecycle, and sensor startup  |
| `SensorFunctions.py`         | TCP client loop — connects, receives text lines, parses positions, sends to PMTW |
| `SensorUI.py`                | Tkinter dialogs for sensor and position-generator configuration                  |
| `SensorLogger.py`            | File logger with default off state and bounded rotation                          |
| `ExternalSensorInterface.py` | ABB-provided interface contract — do not modify                                  |

---

## Architecture

```
PMTW (PickMaster Twin)
  │  Callback: GetRecipeStatus / GetStrobeTime / NewPosition
  │
ExternalSensorTCP          ← main class, one instance per recipe
  ├─ configureSensor()     ← opens TCP + logging config dialog
  ├─ configurePosGen()     ← opens position generator index dialog
  └─ startSensor()         ← spawns one thread per sensor
       │
       └─ SensorFunctions.startSensor()   (per-sensor thread)
            ├─ TCP connect to sensor server
            ├─ Receive TCP text stream in loop
            ├─ Buffer strobe time by AcqNo (trigger line)
            └─ sendNewPositions() → callback.NewPosition(objects)
```

---

## Configuration

### Sensor configuration dialog

Opened by PMTW when the user clicks **Configure** on the External Sensor item.

| Field           | Description                                                         |
| --------------- | ------------------------------------------------------------------- |
| TCP server IP   | IPv4 address of the sensor's TCP server                             |
| TCP server port | Port number (0–65535)                                               |
| Test button     | Opens a 1.5 s test connection; **OK is disabled until test passes** |
| Enable logging  | Checkbox to activate file logging; unchecked by default             |
| Log folder      | Destination folder (created automatically if missing)               |
| File name       | Log filename; default: `ExternalSensor.log`                         |

The sensor config string is stored as `"ip;port"` (e.g. `"192.168.0.9;8500"`).  
The logger config string is stored as `"enabled|folder|filename"` (e.g. `"0|C:\PMScriptsLog|ExternalSensor.log"`). Logging is unchecked by default, and the logger rotates files at 50 MB while retaining the latest 5 rotated logs.

The sensor config persists in the base class dictionary. The logger config persists in `C:\PMScriptsConfig\ExternalSensorTCP.config.json` and is reloaded by sensor ID.

### Position generator configuration dialog

Opened when the user clicks **Configure** on the Item Source item.

| Field                    | Description                                            |
| ------------------------ | ------------------------------------------------------ |
| Position generator index | One or more integer indices (0–1000), separated by `;` |

Stored as `"0"` or `"0;1;2"`.

---

## TCP Text Message Format

The sensor server must send UTF-8 text over a TCP connection.
Each message must end with `LF` (`\n`) or `CRLF` (`\r\n`).

For each acquisition, send exactly two lines in this order:

**Acquisition trigger line** (sent first, once per acquisition):
```text
123
```

**Position line** (sent after trigger):
```text
123,2,100.0,200.0,0.0,0,1.0,0.0,0.0,0.0,0.0,0.0,2,150.0,250.0,90.0,1,1.0,0.0,0.0,0.0,0.0,0.0,2
```

The position line starts with a header (`AcqNo,NumberOfObjects`) followed by `NumberOfObjects`
repetitions of an 11-field object block. Any number of objects is allowed (0, 1, 3, 9, 17, ...).

Header fields:

| Field             | Meaning                                                                    |
| ----------------- | -------------------------------------------------------------------------- |
| `AcqNo`           | Acquisition number linking position to its previously captured strobe time |
| `NumberOfObjects` | Number of object blocks that follow                                        |

Field meaning for each object block:

| Field   | Meaning                             |
| ------- | ----------------------------------- |
| `X`     | Position X                          |
| `Y`     | Position Y                          |
| `RZ`    | Rotation Z                          |
| `Tag`   | Integer tag/identifier for the item |
| `Score` | Match/confidence score              |
| `Val1`  | Custom numeric value 1              |
| `Val2`  | Custom numeric value 2              |
| `Val3`  | Custom numeric value 3              |
| `Val4`  | Custom numeric value 4              |
| `Val5`  | Custom numeric value 5              |
| `Level` | 1=tentative, 2=confirmed            |

Rules for the camera-side message format:

- `,` (comma) is the field separator, not tabs, spaces, or semicolons.
- `AcqNo` is the first field. It may be sent as an integer or as an integral float, for example `123` or `1571.000`.
- The position line must contain exactly `2 + 11 * NumberOfObjects` fields.
- All fields may be sent as numeric values, for example `100`, `100.0`, or `-32.5`.
- `Tag` and `Level` are truncated to integers after parsing (e.g. `1.0` or `1` both become `1`).
- `Z`, `RX` and `RY` are no longer part of the protocol; they are sent to PMTW as `0.0`.
- The `AcqNo` in the position line must match the earlier acquisition trigger line.
- This TCP implementation supports one position line per `AcqNo`.
- The camera does not send the text `acq`; that label is created internally by the parser.

Example payload sent by the camera (one acquisition, two objects):

```text
123\r\n
123,2,100.0,200.0,0.0,0,1.0,0.0,0.0,0.0,0.0,0.0,2,150.0,250.0,90.0,1,1.0,0.0,0.0,0.0,0.0,0.0,2\r\n
```

Runtime behavior:

- The parser is line-based (`CRLF`/`LF`) and supports TCP chunk fragmentation.
- A line with no comma is treated as an acquisition trigger and stores `GetStrobeTime()` for that `AcqNo`.
- A line with a comma must contain `AcqNo,NumberOfObjects` followed by `NumberOfObjects` blocks of `X,Y,RZ,Tag,Score,Val1,Val2,Val3,Val4,Val5,Level`.
- If more object blocks than `NumberOfObjects` are present, the extra blocks are ignored and the mismatch is logged. If fewer are present, the line is rejected.
- The first matching position line reuses the strobe time captured from the earlier trigger line with the same `AcqNo`.
- If a position arrives before its matching trigger, it is discarded and logged.
- If a second position arrives with the same `AcqNo`, it is discarded because the stored strobe entry was already consumed.
- An object block with `X=0`, `Y=0` and `RZ=0` means no part was detected in that slot and is not forwarded to PMTW. With `NumberOfObjects=0`, or when every block is empty, the strobe time is still consumed and a position message with an empty object list is sent, so every acquisition gets one answer.

---

## Position Format Sent to PMTW

```python
{
    'SensorId': sensorId,
  'Time':     strobeTime,         # strobe captured on trigger line for the same AcqNo
    "'0'": {                        # key = quoted index string, one per non-empty object
        'X': float, 'Y': float, 'Z': float,
        'RX': float, 'RY': float, 'RZ': float,
        'Tag': int,
        'Score': float,
        'Val1': float, 'Val2': float, 'Val3': float, 'Val4': float, 'Val5': float,
        'Level': int,               # 1=tentative, 2=confirmed
        'PosGenId': positionGeneratorId,
    },
    "'1'": { ... },                 # additional objects, indexes are re-numbered from 0
}
```

When no part is detected, the position objects are omitted:

```python
{
    'SensorId': sensorId,
    'Time':     strobeTime,
}
```

---

## Logging

When enabled in the sensor config dialog, a `.log` file is written to the configured folder. Logging is unchecked by default to avoid unnecessary disk usage, and the default file name is `ExternalSensor.log`.

The logger is bounded to prevent runaway disk growth: each active log file is capped at 50 MB, it rotates automatically when the cap is reached, and only the latest 5 rotated files are retained. When rollover occurs, a single warning is emitted to `stderr` so disk usage remains controlled even if logging is left enabled for longer than intended.

**Log format:**
```
[2026-08-04 14:32:15.123] [ERROR] [startSensor] Sensor starting. sensorId=1 posGenId=2
[2026-08-04 14:32:15.456] [SUCCESS] [startSensor] Connected to 192.168.0.9:8500
[2026-08-04 14:32:15.900] [SUCCESS] [startSensor] Processing message line: '142'
[2026-08-04 14:32:15.901] [SUCCESS] [startSensor] Stored strobe time for AcqNo=142 time=123456.789
[2026-08-04 14:32:16.001] [SUCCESS] [startSensor] Sent 1 object(s) for AcqNo=142 (declared=1) posGenId=2 time=123456.789
[2026-08-04 14:32:20.777] [ERROR] [startSensor] AcqNo 0043 not in strobe buffer; position discarded.
[2026-08-04 14:35:00.000] [SUCCESS] [startSensor] Socket shutdown in progress; read interrupted by expected close: [WinError 10058] ...
```

**Events logged:**

| Event                                           | Level   |
| ----------------------------------------------- | ------- |
| Sensor thread starting                          | SUCCESS |
| TCP connection established                      | SUCCESS |
| Positions sent to PMTW                          | SUCCESS |
| Strobe time stored for AcqNo trigger            | SUCCESS |
| TCP connection failed                           | ERROR   |
| Socket disconnected                             | ERROR   |
| Socket receive error                            | ERROR   |
| Text parse error (message discarded)            | ERROR   |
| AcqNo not in strobe buffer (position discarded) | ERROR   |
| Invalid NumberOfObjects / malformed payload     | ERROR   |
| Runtime thread exception                        | ERROR   |
| Recipe lifecycle and shutdown steps             | SUCCESS |

### Graceful shutdown behavior

When the recipe is stopped, the TCP listener shuts the socket down gracefully before closing it and uses a short socket timeout during the receive loop. This prevents abrupt thread termination and avoids noisy Windows socket-abort messages that can be mistaken for sensor or protocol failures.

Typical shutdown log sequence:

```text
[2026-08-18 10:02:30.937] [SUCCESS] [ExternalSensorTCP.startSensor] Step 4 done: recipe stop detected.
[2026-08-18 10:02:30.938] [SUCCESS] [ExternalSensorTCP.startSensor] Step 5: starting graceful shutdown for 1 sensor thread(s).
[2026-08-18 10:02:30.938] [SUCCESS] [ExternalSensorTCP.startSensor] Closing TCP socket for sensor=ExternalSensor_1 before thread exit.
[2026-08-18 10:02:30.939] [SUCCESS] [ExternalSensorTCP.startSensor] socket.shutdown(SHUT_RDWR) completed for sensor=ExternalSensor_1.
[2026-08-18 10:02:30.939] [SUCCESS] [startSensor] Socket shutdown in progress; read interrupted by expected close: [WinError 10058] ...
[2026-08-18 10:02:30.940] [SUCCESS] [ExternalSensorTCP.startSensor] StartSensor completed and all threads stopped.
```

> **Note:** If the log folder is not writable, an error is printed to `stderr` and logging continues silently. The sensor runtime is not affected.

> **Inherent gap:** The **Test** button result during config is shown in the UI only — it cannot be written to the log file because the file path has not been confirmed yet at that point.

---

## Examples

Example configurations and integration guides for common sensor types:

- **`example/cognex/`** — Cognex job file
- **`example/keyence/`** — Keyence programs (calibration and ShapeTrax3A)

---

## Extending

This implementation follows the ABB External Sensor interface contract defined in `ExternalSensorInterface.py`. To create a different sensor type:

1. Copy `ExternalSensorTCP.py` and rename it (class name must match file name).
2. Inherit the four base classes: `SensorRuntime, PositionGenerator, SensorConfig, SensorInfo`.
3. Implement `configureSensor(sensorId)`, `configurePosGen(posGenId)`, `startSensor(callBackFunc)`, and `stopSensor()`.
4. Follow the Step 1–5 pattern in `startSensor` (documented in `ExternalSensorInterface.py`).

---

## Contributing

We welcome improvements, bug reports, and feature requests.

1. Open an issue before starting major work if you want to discuss a change or feature.
2. Create a dedicated branch for your fix or feature, for example:
   - `feature/position-parser-improvement`
   - `fix/logger-rotation`
3. Keep changes focused and update the documentation when behavior changes.
4. Open a pull request with a short summary, motivation, and validation notes.

> Please do not open a pull request without a related issue or a clear change description.

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

## Error Reference

| Error code          | Meaning                                                                |
| ------------------- | ---------------------------------------------------------------------- |
| `PortOccupiedError` | Windows socket error 10048 — another process is already using the port |
| WinError 10040      | TCP receive failed because the message payload was too large           |
| WinError 10061      | Connection refused — sensor server is not running or wrong IP/port     |
