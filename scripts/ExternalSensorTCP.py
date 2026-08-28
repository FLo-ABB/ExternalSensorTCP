# ExternalSensorTCP
from ExternalSensorInterface import StoppableThread
from ExternalSensorInterface import SensorInfo
from ExternalSensorInterface import SensorConfig
from ExternalSensorInterface import PositionGenerator
from ExternalSensorInterface import SensorRuntime
import SensorFunctions
import SensorLogger
import threading
import sys
import traceback
import os
import json
import socket


class ExternalSensorTCP(SensorRuntime, PositionGenerator, SensorConfig, SensorInfo):
    name = "ExternalSensorTCP"
    description = (
        "ExternalSensorTCP connects to a TCP/IP external sensor, receives item position data in "
        "three dimensions together with the associated metadata, and forwards the results to "
        "PickMaster Twin/Lite for robot pick-and-place coordination. The sensor IP address and "
        "port are configured in the External Sensor settings, while the position generator index "
        "is configured in the Item Source settings. This implementation supports a single sensor."
    )

    author = "F. LOBERT, ABB"
    version = "1.1"

    allThreads = []
    allSensors = []
    loggerConfigDict: dict = {}
    configFilePath = r"C:\PMScriptsConfig\ExternalSensorTCP.config.json"
    legacyConfigFilePath = r"C:\PMScriptsLog\ExternalSensorTCP.config.json"

    def _get_logger(self) -> SensorLogger.SensorLogger:
        # Returns a logger from the first available sensor config; no-op logger if none configured yet.
        config = next(iter(self.loggerConfigDict.values()), "")
        return SensorLogger.SensorLogger(config)

    def _normalize_id(self, value) -> str:
        if value is None:
            return ""
        # Normalize GUID-like ids to avoid lookup misses due to case/braces/whitespace differences.
        return str(value).strip().strip("{}").lower()

    def _read_config_file(self) -> dict:
        config = {}
        try:
            with open(self.configFilePath, "r", encoding="utf-8") as f:
                config = json.load(f)
                if isinstance(config, dict):
                    return config
        except Exception:
            pass

        # Backward compatibility: if config used to live in log folder, read and migrate it.
        try:
            with open(self.legacyConfigFilePath, "r", encoding="utf-8") as f:
                config = json.load(f)
                if isinstance(config, dict):
                    self._write_config_file(config)
                    return config
        except Exception:
            pass

        return {}

    def _write_config_file(self, config: dict) -> None:
        try:
            os.makedirs(os.path.dirname(self.configFilePath), exist_ok=True)
            with open(self.configFilePath, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
        except Exception:
            pass

    def _save_logger_config_for_sensor(self, sensorId, loggerConfigStr: str) -> None:
        normalizedSensorId = self._normalize_id(sensorId)
        if not normalizedSensorId:
            return
        config = self._read_config_file()
        loggerConfigBySensorId = config.get("loggerConfigBySensorId", {})
        if not isinstance(loggerConfigBySensorId, dict):
            loggerConfigBySensorId = {}
        loggerConfigBySensorId[normalizedSensorId] = loggerConfigStr
        config["loggerConfigBySensorId"] = loggerConfigBySensorId
        self._write_config_file(config)

    def _load_logger_config_for_sensor(self, sensorId) -> str:
        normalizedSensorId = self._normalize_id(sensorId)
        if not normalizedSensorId:
            return ""
        config = self._read_config_file()
        loggerConfigBySensorId = config.get("loggerConfigBySensorId", {})
        if not isinstance(loggerConfigBySensorId, dict):
            return ""
        loggerConfig = loggerConfigBySensorId.get(normalizedSensorId, "")
        return loggerConfig if isinstance(loggerConfig, str) else ""

    def _get_logger_config_for_sensor(self, sensorId) -> str:
        if sensorId is None:
            return ""
        sensorIdNormalized = self._normalize_id(sensorId)
        if sensorIdNormalized in self.loggerConfigDict:
            return self.loggerConfigDict[sensorIdNormalized]
        loggerConfig = self._load_logger_config_for_sensor(sensorId)
        if loggerConfig:
            self.loggerConfigDict[sensorIdNormalized] = loggerConfig
        return loggerConfig

    def exceptHook(self, *args):
        tbType, tbValue, tbTraceback, _ = args[0]
        argsList = []
        i = 0
        while i < len(tbValue.args) and i < 2:
            argsList.append(str(tbValue.args[i]))
            i += 1
        errorMessage = ", ".join(argsList)
        tracebackMessage = str(traceback.format_exception(tbType, tbValue, tbTraceback))
        logMessage = "[ExternalSensorTCP] {}. {}".format(errorMessage, tracebackMessage)
        log = {"LogLevel": 2, "Log": logMessage}
        self.fLogCallback.ShowPythonLog(log)
        self._get_logger().log("ExternalSensorTCP.threadException", errorMessage)

    sys.excepthook = exceptHook

    def configureSensor(self, sensorId):
        try:
            inputTitle: str = "Sensor configuration"
            sensor = SensorFunctions.SensorFunctions()

            if sensorId in self.sensorConfigurationDict:
                inputPort = self.sensorConfigurationDict[sensorId]
            else:
                inputPort = "8500"

            isSensorConfigValid, sensorConfigInfo, loggerConfigStr = sensor.showSensorPortConfigDialog(
                inputTitle, inputPort, self.fLogCallback, self._get_logger_config_for_sensor(sensorId)
            )

            if isSensorConfigValid:
                self.sensorConfigurationDict[sensorId] = sensorConfigInfo
                normalizedSensorId = self._normalize_id(sensorId)
                self.loggerConfigDict[normalizedSensorId] = loggerConfigStr
                self._save_logger_config_for_sensor(sensorId, loggerConfigStr)
                loggerEnabled, _, _ = SensorLogger.deserialize_config(loggerConfigStr)

                SensorLogger.SensorLogger(loggerConfigStr).log(
                    "ExternalSensorTCP.configureSensor",
                    "Configuration saved. sensorId={} TCP={} loggerEnabled={}".format(
                        sensorId, sensorConfigInfo, loggerEnabled
                    ),
                    success=True,
                )

        except Exception as e:
            self._get_logger().log("ExternalSensorTCP.configureSensor", str(e))

    def configurePosGen(self, positionGeneratorId):
        try:
            inputTitle: str = "Position generator configuration"
            sensor = SensorFunctions.SensorFunctions()

            sensorId = self.posGenSensorMapDict.get(positionGeneratorId)
            loggerConfigStr = self._get_logger_config_for_sensor(sensorId)
            logger = SensorLogger.SensorLogger(loggerConfigStr) if loggerConfigStr else self._get_logger()

            if positionGeneratorId in self.posGenConfigurationDict.keys():
                inputIndex = self.posGenConfigurationDict[positionGeneratorId]
            else:
                inputIndex = "0"

            isIndexValid, positionGeneratorIndex = sensor.showPositionGeneratorConfigDialog(
                inputTitle, inputIndex, self.fLogCallback
            )

            if isIndexValid:
                self.posGenConfigurationDict[positionGeneratorId] = positionGeneratorIndex
                logger.log(
                    "ExternalSensorTCP.configurePosGen",
                    "Configuration saved for posGenId={} index={} sensorId={}".format(
                        positionGeneratorId, positionGeneratorIndex, sensorId
                    ),
                    success=True,
                )
            else:
                logger.log(
                    "ExternalSensorTCP.configurePosGen",
                    "Configuration dialog closed without save for posGenId={} sensorId={}".format(
                        positionGeneratorId, sensorId
                    ),
                    success=True,
                )

        except Exception as e:
            self._get_logger().log("ExternalSensorTCP.configurePosGen", str(e))

    def startSensor(self, callBackFunc):  # this interface must be implemented by users.
        try:
            self._get_logger().log(
                "ExternalSensorTCP.startSensor",
                "ENTER startSensor. posGen count={}".format(len(self.posGenSensorMapDict)),
                success=True,
            )

            # Step 1: call classname.monitorRecipeStatus(self, callBackFunc) to monitor the recipe status running in PMTW.
            ExternalSensorTCP.monitorRecipeStatus(self, callBackFunc)
            self._get_logger().log("ExternalSensorTCP.startSensor", "Step 1 done: monitorRecipeStatus started.", success=True)

            # Step 2: start user logic and create one StoppableThread per sensor.
            for positionGeneratorId in self.posGenSensorMapDict:
                sensorId = self.posGenSensorMapDict[positionGeneratorId]
                sensor = SensorFunctions.SensorFunctions()
                sensor.sensorName = self.sensorIdNameMapDict[sensorId]
                thread = StoppableThread(
                    target=sensor.startSensor,
                    args=(
                        callBackFunc,
                        sensorId,
                        positionGeneratorId,
                        self.sensorConfigurationDict[sensorId],
                        self.posGenConfigurationDict[positionGeneratorId],
                        self.fLogCallback,
                        self._get_logger_config_for_sensor(sensorId),
                    ),
                )
                self.allThreads.append(thread)
                self.allSensors.append(sensor)
                self._get_logger().log(
                    "ExternalSensorTCP.startSensor",
                    "Prepared thread for sensorId={} posGenId={}".format(sensorId, positionGeneratorId),
                    success=True,
                )

            # Step 3: start all threads in self.allThreads.
            threading.excepthook = self.exceptHook
            for td in self.allThreads:
                td.start()

            self._get_logger().log("ExternalSensorTCP.startSensor", "All sensor threads started.", success=True)

            # Step 4: call classname.waitForRecipeStop(self) to wait for the stop signal from PMTW.
            self._get_logger().log("ExternalSensorTCP.startSensor", "Step 4: waiting for recipe stop.", success=True)
            ExternalSensorTCP.waitForRecipeStop(self)
            self._get_logger().log("ExternalSensorTCP.startSensor", "Step 4 done: recipe stop detected.", success=True)

            # Step 5: stop all threads in self.allThreads.
            self._get_logger().log(
                "ExternalSensorTCP.startSensor",
                "Step 5: starting graceful shutdown for {} sensor thread(s).".format(len(self.allSensors)),
                success=True,
            )
            for sensor in self.allSensors:
                sensor.isRunning = False
                if sensor.server is not None:
                    self._get_logger().log(
                        "ExternalSensorTCP.startSensor",
                        "Closing TCP socket for sensor={} before thread exit.".format(getattr(sensor, "sensorName", "unknown")),
                        success=True,
                    )
                    try:
                        sensor.server.shutdown(socket.SHUT_RDWR)
                        self._get_logger().log(
                            "ExternalSensorTCP.startSensor",
                            "socket.shutdown(SHUT_RDWR) completed for sensor={}.".format(getattr(sensor, "sensorName", "unknown")),
                            success=True,
                        )
                    except OSError as ex:
                        self._get_logger().log(
                            "ExternalSensorTCP.startSensor",
                            "socket shutdown warning for sensor={} : {}".format(getattr(sensor, "sensorName", "unknown"), str(ex)),
                        )
                    sensor.server.close()
                    self._get_logger().log(
                        "ExternalSensorTCP.startSensor",
                        "socket.close() completed for sensor={}.".format(getattr(sensor, "sensorName", "unknown")),
                        success=True,
                    )

            for td in self.allThreads:
                self._get_logger().log(
                    "ExternalSensorTCP.startSensor",
                    "Stopping sensor thread {}.".format(td.name),
                    success=True,
                )
                td.stop()

            logMessage = "[ExternalSensorTCP] {}.".format("StartSensor: all threads stopped")
            log = {"LogLevel": 0, "Log": logMessage}
            self.fLogCallback.ShowPythonLog(log)

            self._get_logger().log("ExternalSensorTCP.startSensor", "StartSensor completed and all threads stopped.", success=True)

        except Exception as e:
            self._get_logger().log("ExternalSensorTCP.startSensor", str(e))
            logMessage = "[ExternalSensorTCP] {}.".format("Python Error: Failed to start sensor")
            log = {"LogLevel": 2, "Log": logMessage}
            self.fLogCallback.ShowPythonLog(log)

    def stopSensor(self):
        logMessage = "[ExternalSensorTCP] {}.".format("StopSensor: stop sensor")
        log = {"LogLevel": 0, "Log": logMessage}
        self.fLogCallback.ShowPythonLog(log)
