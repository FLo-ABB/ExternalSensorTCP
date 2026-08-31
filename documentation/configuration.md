# Configuration

## Sensor configuration dialog

Opened by PMTW when the user clicks **Configure** on the External Sensor item.

| Field           | Description                                                          |
| --------------- | ---------------------------------------------------------------------|
| TCP server IP   | IPv4 address of the sensor's TCP server                              |
| TCP server port | Port number (0–65535)                                                |
| Test button     | Opens a 1.5 s test connection; **OK is disabled until test passes**  |
| Enable logging  | Checkbox to activate file logging; unchecked by default              |
| Log folder      | Destination folder (created automatically if missing)               |

The sensor config persists in the base class dictionary. The logger config persists beside the deployed scripts in `%PROGRAMDATA%\ABB\PickMaster\PMScripts\ExternalSensorTCP.config.json` and is reloaded by sensor ID.

## Sensor configuration

The sensor configuration dialog is used to set:

- TCP server IP address
- TCP server port
- log enable state
- log folder

### Default values

- IP: `192.168.0.9`
- Port: `8500`
- Log enabled: `False`
- Log folder: `%PROGRAMDATA%\ABB\PickMaster\PMScripts\`
- Log file name: fixed to `ExternalSensor.log`

### Config string format

The sensor connection string is stored as:

```text
"ip;port"
```

Example:

```text
"192.168.0.9;8500"
```

The logger config string is stored as:

```text
"enabled|folder"
```

Example:

```text
"0|%PROGRAMDATA%\ABB\PickMaster\PMScripts\"
```

## Position generator configuration dialog

Opened when the user clicks **Configure** on the Item Source item.

| Field                    | Description                                            |
| ------------------------ | -------------------------------------------------------|
| Position generator index | One or more integer indices (0–1000), separated by `;` |

## Position generator configuration

The position generator configuration stores the configuration used for the generator index, usually in the format:

```text
"0"
```

or multiple entries separated with `;`:

```text
"0;1;2"
```

## Runtime behavior

During startup, the runtime loads the saved logger configuration for the current sensor ID and reuses it when the configuration dialog is reopened.

The logger settings are persisted in:

```text
%PROGRAMDATA%\ABB\PickMaster\PMScripts\ExternalSensorTCP.config.json
```
