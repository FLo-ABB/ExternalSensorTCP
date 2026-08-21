# This software is provided 'as-is', without any express or
# implied warranty. In no event will ABB be held liable for
# any damages arising from the use of this software.

import socket
import re
from typing import Any
from collections import OrderedDict
import SensorLogger
import SensorUI

TCPServerAddress = "192.168.0.9"


class PortOccupiedError(Exception):
    # PortOccupiedError will be thrown when the port is occupied.
    def __init__(self, *args: Any) -> None:
        super().__init__()
        self.args = (
            "{}. Sensor name: {} , Port: {}".format(
                str(args[0][2]), str(args[0][0]), str(args[0][1])
            ),
        )


class SensorFunctions:
    # This path need to be created by users to store the SensorLog. The SensorLog includes the received item positions.
    logPath = r"C:\PMScriptsLog\SensorLog.txt"
    isRunning = True
    sensorName = ""
    server: socket.socket | None = None

    def showLog(self, message: str, logLevel: int, logCallback):
        logMessage = "[ExternalSensorTCP] {}.".format(message)
        log = {"LogLevel": logLevel, "Log": logMessage}
        logCallback.ShowPythonLog(log)

    def parseSensorConfig(self, configInfo: str):
        # Keep backward compatibility with existing port-only configuration.
        defaultAddress = TCPServerAddress
        defaultPort = "8500"

        if configInfo is None:
            return defaultAddress, int(defaultPort)

        sensorConfig = str(configInfo).strip()
        if not sensorConfig:
            return defaultAddress, int(defaultPort)

        if ";" in sensorConfig:
            parts = sensorConfig.split(";", 1)
            ipAddress = parts[0].strip()
            port = parts[1].strip()
            if ipAddress and port.isdigit() and 0 <= int(port) <= 65535:
                return ipAddress, int(port)
            return defaultAddress, int(defaultPort)

        if sensorConfig.isdigit() and 0 <= int(sensorConfig) <= 65535:
            return defaultAddress, int(sensorConfig)

        return defaultAddress, int(defaultPort)

    def showSensorPortConfigDialog(self, inputTitle: str, configInfo: str, callBackFunc, loggerConfigStr: str = ""):
        try:
            defaultAddress, defaultPort = self.parseSensorConfig(configInfo)
            isConfigValid, serverConfig, newLoggerConfig = SensorUI.show_sensor_config_dialog(
                inputTitle,
                str(defaultAddress),
                str(defaultPort),
                loggerConfigStr,
            )

            return isConfigValid, serverConfig, newLoggerConfig
        except Exception:
            return False, [], ""

    def showPositionGeneratorConfigDialog(self, inputTitle: str, configInfo: str, callBackFunc):
        return SensorUI.show_position_generator_config_dialog(inputTitle, configInfo)

    def startSensor(
        self, callback, sensorId, positionGeneratorId,
        sensorConfigInfo, positionGeneratorConfigInfo, logCallback, loggerConfigStr: str = ""
    ):
        # Initialize a TCP client. The server receives messages and forwards positions to RT.
        logger = SensorLogger.SensorLogger(loggerConfigStr)
        logger.log("startSensor", "Sensor starting. sensorId={} posGenId={}".format(sensorId, positionGeneratorId), success=True)
        recvBuffer = ""
        acqStrobeDict = OrderedDict()
        maxLimitAcq = 100

        def recordPositions(objects):
            with open(self.logPath, "a") as f:
                pattern = "Score|Time|SensorId"
                for key in objects.keys():
                    if not re.match(pattern, key):
                        f.write(
                            str(objects[key]["X"])
                            + ", "
                            + str(objects[key]["Y"])
                            + ", "
                            + str(objects[key]["Z"])
                            + ", "
                            + str(objects[key]["RZ"])
                            + "\n"
                        )

        def dictLimitCheck(orderedDict, maxLimit: int):
            if len(orderedDict) >= maxLimit:
                orderedDict.popitem(last=False)

        # Position line field order after AcqNo, matching the PMTW position object schema.
        posFieldNames = (
            "X", "Y", "Z", "RX", "RY", "RZ",
            "Tag", "Score", "Val1", "Val2", "Val3", "Val4", "Val5", "Level",
        )
        posFieldCount = len(posFieldNames)
        # Fields sent as integers on the PMTW position object; all others stay float.
        intFieldNames = ("Tag", "Level")

        def parseSimpleTextLine(msgLine: str):
            # Supported text protocol:
            # 1) Acquisition trigger line: "AcqNo"
            # 2) Position line: "AcqNo,X,Y,Z,RX,RY,RZ,Tag,Score,Val1,Val2,Val3,Val4,Val5,Level"
            if "," not in msgLine:
                acqNo = msgLine.strip()
                if not re.match(r"^\d+$", acqNo):
                    raise ValueError("Expected acquisition number when no comma is present")
                return ("acq", acqNo)

            parts = msgLine.split(",")
            if len(parts) != 1 + posFieldCount:
                raise ValueError(
                    "Expected {} fields: AcqNo,{}".format(1 + posFieldCount, ",".join(posFieldNames))
                )

            acqNo = parts[0].strip()
            if not re.match(r"^\d+$", acqNo):
                raise ValueError("Invalid AcqNo in position line")

            posFields = {}
            for name, rawValue in zip(posFieldNames, parts[1:]):
                value = float(rawValue.strip())
                posFields[name] = int(value) if name in intFieldNames else value
            return ("pos", posFields, acqNo)

        def isEmptyPosition(posFields: dict) -> bool:
            # The camera sends X=0, Y=0, RZ=0 for an acquisition where no part was detected.
            return posFields["X"] == 0.0 and posFields["Y"] == 0.0 and posFields["RZ"] == 0.0

        def sendSimplePosition(posFields: dict, strobeTime: float):
            objects = {
                "SensorId": sensorId,
                "Time": strobeTime,
            }
            if not isEmptyPosition(posFields):
                objects["'0'"] = {
                    **posFields,
                    "PosGenId": positionGeneratorId,
                }
            callback.NewPosition(objects)

        ############################
        # TCP Client
        try:
            tcpServerAddress, tcpServerPort = self.parseSensorConfig(sensorConfigInfo)
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.settimeout(1.0)
            self.server.connect((tcpServerAddress, tcpServerPort))
            logger.log("startSensor", "Connected to {}:{}".format(tcpServerAddress, tcpServerPort), success=True)

        except OSError as ex:
            logger.log("startSensor", "Connection failed: {}".format(str(ex)))
            if ex.errno == 10048:
                raise PortOccupiedError((self.sensorName, sensorConfigInfo, ex.args[1]))
            raise ex
        while self.isRunning:
            try:
                data = self.server.recv(4096)
                if not data:
                    logger.log("startSensor", "Socket disconnected; worker stopped.")
                    self.showLog("Socket closed/disconnected error!", 2, logCallback)
                    return
                recv_str = data.decode("utf-8")
                logger.log(
                    "startSensor",
                    "Received raw TCP chunk ({} bytes): {}".format(len(data), repr(recv_str)),
                    success=True,
                )
                recvBuffer += recv_str

                # Handle stream framing safely: process only complete CR/LF or LF-terminated lines.
                lines = recvBuffer.splitlines(keepends=True)
                recvBuffer = ""
                for line in lines:
                    if line.endswith("\n") or line.endswith("\r"):
                        cleanLine = line.rstrip("\r\n").strip()
                        if not cleanLine:
                            continue
                        logger.log("startSensor", "Processing message line: {}".format(repr(cleanLine)), success=True)
                        parsedLine = parseSimpleTextLine(cleanLine)

                        if parsedLine[0] == "acq":
                            acqNo = parsedLine[1]
                            strobeTime = callback.GetStrobeTime()
                            dictLimitCheck(acqStrobeDict, maxLimitAcq)
                            acqStrobeDict[acqNo] = strobeTime
                            logger.log(
                                "startSensor",
                                "Stored strobe time for AcqNo={} time={}".format(acqNo, strobeTime),
                                success=True,
                            )
                            continue

                        _, posFields, acqNo = parsedLine
                        if acqNo not in acqStrobeDict:
                            logger.log(
                                "startSensor",
                                "AcqNo {} not in strobe buffer; position discarded.".format(acqNo),
                            )
                            continue

                        strobeTime = acqStrobeDict.pop(acqNo)
                        sendSimplePosition(posFields, strobeTime)
                        if isEmptyPosition(posFields):
                            logger.log(
                                "startSensor",
                                "Sent empty object list for AcqNo={} (no part detected) time={}".format(
                                    acqNo, strobeTime
                                ),
                                success=True,
                            )
                        else:
                            logger.log(
                                "startSensor",
                                "Sent simple text position AcqNo={} X={} Y={} posGenId={} time={}".format(
                                    acqNo, posFields["X"], posFields["Y"], positionGeneratorId, strobeTime
                                ),
                                success=True,
                            )
                    else:
                        recvBuffer = line
                        logger.log(
                            "startSensor",
                            "Buffered partial message fragment: {}".format(repr(recvBuffer)),
                            success=True,
                        )
            except socket.timeout:
                if not self.isRunning:
                    logger.log("startSensor", "Socket read timeout during shutdown; exiting cleanly.", success=True)
                    return
                continue
            except OSError as ex:
                if ex.errno in (10053, 10054, 10058) and not self.isRunning:
                    logger.log(
                        "startSensor",
                        "Socket shutdown in progress; read interrupted by expected close: {}".format(str(ex)),
                        success=True,
                    )
                    return
                if ex.errno in (10053, 10054, 10058):
                    logger.log(
                        "startSensor",
                        "Socket disconnected during read: {}".format(str(ex)),
                    )
                    self.showLog("Socket closed/disconnected error!", 2, logCallback)
                    return
                logger.log("startSensor", "Socket error: {}".format(str(ex)))
                if ex.errno == 10040:
                    self.showLog("Received TCP payload is too large. Please reduce the message size.", 2, logCallback)
                    return
                raise ex
            except ValueError as ex:
                logger.log("startSensor", "Text parse error; message discarded: {}".format(str(ex)))
                failedLine = repr(cleanLine) if "cleanLine" in locals() else "unavailable"
                logger.log("startSensor", "Failed line content: {}".format(failedLine))
                self.showLog(
                    "Invalid text format. Expected 'AcqNo' or 'AcqNo,X,Y,Z,RX,RY,RZ,Tag,Score,Val1,Val2,Val3,Val4,Val5,Level'.",
                    2,
                    logCallback,
                )
            except SystemExit:
                logger.log("startSensor", "Shutdown requested; exiting socket listener cleanly.", success=True)
                return
            except Exception as ex:
                logger.log("startSensor", "Runtime error: {}".format(str(ex)))
                raise ex
        ############################
