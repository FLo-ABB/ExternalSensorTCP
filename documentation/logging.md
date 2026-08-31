# Logging

## Default behavior

Logging is unchecked by default to avoid unnecessary disk usage. The log file name is fixed to:

```text
ExternalSensor.log
```

The default log folder is:

```text
%PROGRAMDATA%\ABB\PickMaster\PMScripts\
```

When enabled, the logger keeps one background writer alive for the PickMaster
process lifetime. This is intentional: logging is used during continuous
commissioning in the integrator workshop.

The fixed name ensures rotation only manages files created by this logger.

## Rotation policy

To prevent uncontrolled log growth, the logger uses a bounded rotation policy:

- maximum active file size: 50 MB
- rotate when file reaches the limit
- keep only the latest 5 rotated files

This prevents a single run from creating a continuously growing log file that can consume a large amount of disk space.

## Sample log entries

```text
[2026-08-04 14:32:15.123] [ERROR] [startSensor] Sensor starting. sensorId=1 posGenId=2
[2026-08-04 14:32:15.456] [SUCCESS] [startSensor] Connected to 192.168.0.9:8500
[2026-08-04 14:32:15.900] [SUCCESS] [startSensor] Processing message line: '142'
[2026-08-04 14:32:15.901] [SUCCESS] [startSensor] Stored strobe time for AcqNo=142 time=123456.789
[2026-08-04 14:32:16.001] [SUCCESS] [startSensor] Sent 1 object(s) for AcqNo=142 (declared=1) posGenId=2 time=123456.789
[2026-08-04 14:32:20.777] [ERROR] [startSensor] AcqNo 0043 not in strobe buffer; position discarded.
[2026-08-04 14:35:00.000] [SUCCESS] [startSensor] Socket shutdown in progress; read interrupted by expected close: [WinError 10058] ...
```

## Typical log events

- sensor start
- TCP connection success or failure
- strobe time storage
- positions sent to PMTW
- malformed text or invalid object block
- shutdown and socket close

## Events reference

| Event                                           | Level   |
| ------------------------------------------------| --------|
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

See [Architecture](architecture.md) for the graceful shutdown log sequence.

## Rotation behavior

If the log file reaches the 50 MB limit, the current active file is renamed and a new one is created.
