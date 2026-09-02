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

## Position generator and item matching

The position generator index is not just a technical detail. It is the link between the external sensor and the PMTW item-source configuration, but it is decided at configuration time, not per detected object.

Each position generator maps to exactly one sensor connection: `posGenSensorMapDict` binds a `posGenId` to a `sensorId`, and `SensorFunctions.startSensor()` runs one TCP connection per position generator (see [Protocol](protocol.md)). The TCP text message itself carries only `X,Y,RZ,Tag,Score,Val1-5,Level` — there is no field the sensor can use to pick a different `PosGenId` for an individual detection. Every object received on a given connection is stamped with that connection's fixed `PosGenId`.

Practical implication: if PMTW needs to distinguish multiple item classes (for illustration, "square" items vs. "circle" items), each class needs its own position generator, mapped to its own sensor entry and TCP connection — for example:

- position generator index `0`, connected to sensor A, used only for square items
- position generator index `1`, connected to sensor B (or another connection to the same physical device), used only for circle items

The external sensor developer and the PickMaster configuration engineer must agree on this mapping ahead of time: which generator index is configured for which connection, and what that connection is expected to report. This is a configuration-level and connection-level agreement, not something negotiated per message.

### The configured index string is currently a placeholder

The value the user types into the **Position generator index** field (`"0"`, `"0;1;2"`, ...) is saved into `posGenConfigurationDict` and passed into `SensorFunctions.startSensor()` as `positionGeneratorConfigInfo`. In the current implementation, that parameter is received but **never read** inside `startSensor()` — it has no effect on parsing, filtering, or on the object sent to PMTW. Today the only value that actually reaches PMTW is `positionGeneratorId` (the generator's own identifier), always the same for every object on that connection.

In other words, the index the user enters currently exists to identify/label the generator in the configuration UI and in log messages, but it is not wired into any decision made while processing TCP data.

This is intentional headroom for extension, not a limitation to work around silently. Examples of what a developer could implement using `positionGeneratorConfigInfo`, without breaking the one-generator-per-connection model:

- **Tag allow-list / validation**: parse `"0;1;2"` as a set of expected `Tag` values for this generator, and log a warning (or drop the object) when an incoming `Tag` is not in that set — useful to catch a misconfigured or miswired sensor early.
- **Per-generator post-processing**: use the configured index to select a coordinate offset, scale factor, or unit conversion that only applies to this generator's connection, when the same `SensorFunctions` code is reused across multiple generators with slightly different physical setups.
- **Diagnostics and traceability**: include the configured index in log messages (`SensorLogger`) so operators can confirm, from the log file alone, which configured index was active for a given connection during troubleshooting.
- **Splitting a single mixed-class stream** (a larger change): if a future protocol version adds a class/type selector to the TCP object block (see the [Known limitation](protocol.md#known-limitation-2d-only-positions) section for the pattern to follow), `positionGeneratorConfigInfo` could be used to decide which `Tag`/class values this particular generator instance should accept, effectively demultiplexing one physical sensor feed into several generators. This is not implemented today and would require protocol and code changes.

If your project does not need any of this, the index field can safely be treated as a simple label with no runtime behavior.

## Runtime behavior

During startup, the runtime loads the saved logger configuration for the current sensor ID and reuses it when the configuration dialog is reopened.

The logger settings are persisted in:

```text
%PROGRAMDATA%\ABB\PickMaster\PMScripts\ExternalSensorTCP.config.json
```
