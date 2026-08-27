# Installation

## Requirements

- PickMaster Twin/Lite with External Sensor support
- A PickMaster installation with Python 3.12 support
- Access to the PM scripts directory under `%PROGRAMDATA%\ABB\PickMaster\PMScripts\`

## Deployment

Copy the runtime script and its companion Python files from the repository's `scripts/` folder into the PickMaster script folder:

```text
%PROGRAMDATA%\ABB\PickMaster\PMScripts\
```

At minimum, copy these files together:

- `scripts/ExternalSensorTCP.py`
- `scripts/ExternalSensorInterface.py`
- `scripts/SensorFunctions.py`
- `scripts/SensorLogger.py`
- `scripts/SensorUI.py`

In PickMaster, add an **External Sensor**, open **Configuration**, and enter `ExternalSensorTCP.py` as the script name. The name must match the Python file in the `PMScripts` directory. The script is loaded by PickMaster Runtime through the External Sensor interface, so the External Sensor must be configured before creating its associated Position Generator.

Python scripts are not included in Pack&Go archives. Copy the files manually when transferring a solution to another PC. For details about External Sensor configuration, Python interfaces, and deployment requirements, see Chapter 5.2, **External sensor**, in *Application manual - PickMaster® Twin - PowerPac*, or the corresponding **External Sensor** chapter in *Application manual - PickMaster® Lite*.

## Verification

After deployment, confirm that the module loads correctly in the configured PM runtime and that the sensor configuration dialog opens as expected.

## Important notes

- The logger is off by default.
- The default log folder is `C:\PMScriptsLog`.
- The default log file is `ExternalSensor.log`.
- If the log folder is not writable, the logger prints a warning to `stderr` but the runtime continues.
