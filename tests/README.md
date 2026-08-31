# Tests

Automated tests for the `ExternalSensorTCP` scripts, using two mocks:

- **`mocks/mock_external_sensor.py`** — `MockExternalSensorServer`, a mock TCP server that
  simulates the external sensor hardware. It can send well-formed protocol lines
  (acquisition trigger / position lines) as well as intentionally **incorrect data
  formats** (garbage text, malformed field counts, etc.) to exercise error handling.
- **`mocks/mock_pickmaster.py`** — `MockPickMaster`, a reliable stand-in for the PickMaster
  Twin/Lite (PMTW) callback object (`GetStrobeTime`, `NewPosition`, `GetRecipeStatus`,
  `ShowPythonLog`). It always behaves correctly and records everything it receives so
  tests can make assertions on it.

## Running

```bash
pip install pytest
pytest
```

## Layout

- `conftest.py` — adds `scripts/` to `sys.path` so tests can `import SensorFunctions` etc.
- `mocks/` — the two mocks described above.
- `test_sensor_logger.py` — tests logger configuration, disabled logging, directory
  creation, line formatting, singleton worker startup, and bounded rotation.
- `test_sensor_functions_integration.py` — end-to-end tests that start
  `SensorFunctions.startSensor` against the mock sensor server and mock PickMaster,
  covering valid data, zero-object acquisitions, incorrect/malformed data, out-of-order
  messages, and client disconnects.
