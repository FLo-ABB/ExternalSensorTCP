# Installation

## Requirements

- PickMaster Twin/Lite with External Sensor support
- Python 3.10+
- Access to the PM scripts directory under `%PROGRAMDATA%\ABB\PickMaster\PMScripts\`

## Deployment

Copy the project files into the PM scripts folder used by your installation, typically:

```text
%PROGRAMDATA%\ABB\PickMaster\PMScripts\
```

The project expects these files to be present:

- `ExternalSensorTCP.py`
- `SensorFunctions.py`
- `SensorUI.py`
- `SensorLogger.py`
- `ExternalSensorInterface.py`

## Verification

After deployment, confirm that the module loads correctly in the configured PM runtime and that the sensor configuration dialog opens as expected.

## Important notes

- The logger is off by default.
- The default log folder is `C:\PMScriptsLog`.
- The default log file is `ExternalSensor.log`.
- If the log folder is not writable, the logger prints a warning to `stderr` but the runtime continues.
