# TCP Protocol

## Message format

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
| ----------------- | --------------------------------------------------------------------------|
| `AcqNo`           | Acquisition number linking position to its previously captured strobe time |
| `NumberOfObjects` | Number of object blocks that follow                                       |

Field meaning for each object block:

| Field   | Meaning                             |
| ------- | ------------------------------------|
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

### Critical requirements

> **Frame/acquisition trigger:** Must be sent immediately when the camera is triggered. Delays will cause position matching errors in PickMaster.
>
> **Position message:** Must always be sent for every frame, even when no objects are found. Send `AcqNo,0` (zero objects) if needed. If omitted, PickMaster will emit warnings that positions are missing.

## Parser behavior

- The parser is line-based (`CRLF`/`LF`) and supports TCP chunk fragmentation.
- A line with no comma is treated as an acquisition trigger and stores `GetStrobeTime()` for that `AcqNo`.
- A line with a comma must contain `AcqNo,NumberOfObjects` followed by `NumberOfObjects` blocks of `X,Y,RZ,Tag,Score,Val1,Val2,Val3,Val4,Val5,Level`.
- If more object blocks than `NumberOfObjects` are present, the extra blocks are ignored and the mismatch is logged. If fewer are present, the line is rejected.
- The first matching position line reuses the strobe time captured from the earlier trigger line with the same `AcqNo`.
- If a position arrives before its matching trigger, it is discarded and logged.
- If a second position arrives with the same `AcqNo`, it is discarded because the stored strobe entry was already consumed.
- An object block with `X=0`, `Y=0` and `RZ=0` means no part was detected in that slot and is not forwarded to PMTW. With `NumberOfObjects=0`, or when every block is empty, the strobe time is still consumed and a position message with an empty object list is sent, so every acquisition gets one answer.

## Position format sent to PMTW

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
