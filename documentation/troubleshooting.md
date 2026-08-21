# Troubleshooting

## Common symptoms

### TCP connection fails

**Symptoms**
- connection refused
- timeout during the Test step
- no sensor data received

**Checks**
- confirm the sensor IP and port are correct
- confirm the sensor server is running
- verify the port is not already in use by another process
- verify no firewall or network policy is blocking the connection

### No positions are sent to PMTW

**Symptoms**
- the TCP connection is active
- no objects appear

**Checks**
- confirm the sensor sends trigger and position lines
- verify that the `AcqNo` in the position line matches the trigger line
- review the log for malformed payloads or invalid `NumberOfObjects` values
- confirm that the data contains non-empty object blocks and not only zero-valued empty slots

### Logging does not appear

**Symptoms**
- no log file is created
- no new entries are written

**Checks**
- confirm the logging checkbox is enabled in the sensor configuration dialog
- verify the log folder exists or can be created
- verify the log file name is valid
- confirm the folder is writable by the current user

### Log file keeps rotating too often

**Symptoms**
- a lot of rotated files appear
- a warning is printed repeatedly

**Checks**
- reduce the volume of logged data
- leave logging disabled unless required for diagnostics
- confirm the sensor is not producing an excessively large stream of messages

## Log folder not writable

If the configured folder cannot be created or written, the logger prints an error to `stderr` and continues without crashing the runtime.

This behavior is intentional: the sensor runtime continues to operate even if the logger cannot persist to disk.

## Useful diagnostic actions

- enable logging only for short debugging periods
- test the TCP connection before starting the recipe
- inspect `AcqNo` mismatches and malformed payload warnings
- review the latest rotated files before deleting old logs
