# Architecture

## Project structure

| File                              | Role                                                                             |
| --------------------------------- | ---------------------------------------------------------------------------------|
| `scripts/ExternalSensorTCP.py`    | Main runtime — orchestrates configuration, thread lifecycle, and sensor startup  |
| `scripts/SensorFunctions.py`      | TCP client loop — connects, receives text lines, parses positions, sends to PMTW |
| `scripts/SensorUI.py`             | Tkinter dialogs for sensor and position-generator configuration                  |
| `scripts/SensorLogger.py`         | File logger with default off state and bounded rotation                          |
| `scripts/ExternalSensorInterface.py` | ABB-provided interface contract — do not modify                               |

## Runtime flow

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

## Graceful shutdown behavior

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

## Extending

This implementation follows the ABB External Sensor interface contract defined in `scripts/ExternalSensorInterface.py`. To create a different sensor type:

1. Copy `scripts/ExternalSensorTCP.py` and rename it (class name must match file name).
2. Inherit the four base classes: `SensorRuntime, PositionGenerator, SensorConfig, SensorInfo`.
3. Implement `configureSensor(sensorId)`, `configurePosGen(posGenId)`, `startSensor(callBackFunc)`, and `stopSensor()`.
4. Follow the Step 1–5 pattern in `startSensor` (documented in `scripts/ExternalSensorInterface.py`).
