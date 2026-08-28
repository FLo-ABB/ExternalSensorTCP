"""Mock PickMaster Twin/Lite (PMTW) runtime callback.

PMTW is the reliable side of the integration: it always answers strobe time
requests, records every position/log call it receives, and reports recipe
status until told to stop. Tests use this mock in place of the real
``callBackFunc``/``logCallback`` objects passed into
``SensorFunctions.startSensor``.
"""

import itertools
import threading


class MockPickMaster:
    """Reliable stand-in for the PMTW callback object.

    Implements the subset of the PMTW interface used by SensorFunctions:
      - GetStrobeTime()
      - NewPosition(objects)
      - GetRecipeStatus()
      - ShowPythonLog(log)
    """

    def __init__(self, initial_recipe_status: int = 1) -> None:
        self._lock = threading.Lock()
        self._strobe_counter = itertools.count(1)
        self.recipe_status = initial_recipe_status

        self.strobe_times: list = []
        self.positions: list = []
        self.logs: list = []

    # --- PMTW callback interface -------------------------------------------------
    def GetStrobeTime(self):
        with self._lock:
            strobe_time = float(next(self._strobe_counter))
            self.strobe_times.append(strobe_time)
            return strobe_time

    def NewPosition(self, objects: dict) -> None:
        with self._lock:
            self.positions.append(objects)

    def GetRecipeStatus(self) -> int:
        with self._lock:
            return self.recipe_status

    def ShowPythonLog(self, log: dict) -> None:
        with self._lock:
            self.logs.append(log)

    # --- Test helpers -------------------------------------------------------------
    def stop_recipe(self) -> None:
        # Simulates PMTW signaling the recipe/production has stopped.
        with self._lock:
            self.recipe_status = 0

    def wait_for_position_count(self, count: int, timeout: float = 5.0) -> bool:
        import time

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            with self._lock:
                if len(self.positions) >= count:
                    return True
            time.sleep(0.01)
        with self._lock:
            return len(self.positions) >= count

    def wait_for_log_containing(self, substring: str, timeout: float = 5.0) -> bool:
        import time

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            with self._lock:
                if any(substring in entry.get("Log", "") for entry in self.logs):
                    return True
            time.sleep(0.01)
        with self._lock:
            return any(substring in entry.get("Log", "") for entry in self.logs)
