# Configuration

## Sensor configuration

The sensor configuration dialog is used to set:

- TCP server IP address
- TCP server port
- log enable state
- log folder
- log file name

### Default values

- IP: `192.168.0.9`
- Port: `8500`
- Log enabled: `False`
- Log folder: `C:\PMScriptsLog`
- File name: `ExternalSensor.log`

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
"enabled|folder|filename"
```

Example:

```text
"0|C:\PMScriptsLog|ExternalSensor.log"
```

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
C:\PMScriptsConfig\ExternalSensorTCP.config.json
```
