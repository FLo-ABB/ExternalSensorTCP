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

        # Field order of one object block, repeated NumberOfObjects times after "AcqNo,NumberOfObjects".
        posFieldNames = (
            "X", "Y", "RZ",
            "Tag", "Score", "Val1", "Val2", "Val3", "Val4", "Val5", "Level",
        )
        posFieldCount = len(posFieldNames)
        # Fields sent as integers on the PMTW position object; all others stay float.
        intFieldNames = ("Tag", "Level")

        def normalizeAcqNo(rawValue: str) -> str:
            value = float(rawValue.strip())
            if value < 0 or value != int(value):
                raise ValueError("Invalid AcqNo value: {}".format(rawValue.strip()))
            return str(int(value))

        def parseSimpleTextLine(msgLine: str):
            # Supported text protocol:
            # 1) Acquisition trigger line: "AcqNo"
            # 2) Position line: "AcqNo,NumberOfObjects" followed by NumberOfObjects blocks of
            #    "X,Y,RZ,Tag,Score,Val1,Val2,Val3,Val4,Val5,Level"
            if "," not in msgLine:
                return ("acq", normalizeAcqNo(msgLine))

            parts = [part.strip() for part in msgLine.split(",")]
            if len(parts) < 2:
                raise ValueError("Position line must contain at least AcqNo and NumberOfObjects")

            acqNo = normalizeAcqNo(parts[0])

            declaredCount = float(parts[1])
            if declaredCount < 0 or declaredCount != int(declaredCount):
                raise ValueError("Invalid NumberOfObjects value: {}".format(parts[1]))
            declaredCount = int(declaredCount)

            payload = parts[2:]
            if len(payload) % posFieldCount != 0:
                raise ValueError(
                    "Object data must be a multiple of {} fields ({}), got {}".format(
                        posFieldCount, ",".join(posFieldNames), len(payload)
                    )
                )
            availableCount = len(payload) // posFieldCount
            if declaredCount > availableCount:
                raise ValueError(
                    "NumberOfObjects={} but only {} object block(s) received".format(
                        declaredCount, availableCount
                    )
                )

            posList = []
            for index in range(declaredCount):
                block = payload[index * posFieldCount:(index + 1) * posFieldCount]
                posFields = {}
                for name, rawValue in zip(posFieldNames, block):
                    value = float(rawValue)
                    posFields[name] = int(value) if name in intFieldNames else value
                posList.append(posFields)
            return ("pos", posList, acqNo, declaredCount, availableCount)

        def isEmptyPosition(posFields: dict) -> bool:
            # The camera sends X=0, Y=0, RZ=0 for an object slot where no part was detected.
            return posFields["X"] == 0.0 and posFields["Y"] == 0.0 and posFields["RZ"] == 0.0

        def sendNewPositions(posList: list, strobeTime: float):
            # Define positions and call the callback function to return positions to PMTW.
            objects = {"SensorId": sensorId}
            objects.update({"Time": strobeTime})
            sentCount = 0
            for posFields in posList:
                if isEmptyPosition(posFields):
                    continue
                key = "'" + str(sentCount) + "'"
                newPos = {key: {"X": posFields["X"],
                                "Y": posFields["Y"],
                                "Z": 0.0,
                                "RX": 0.0,
                                "RY": 0.0,
                                "RZ": posFields["RZ"],
                                "Tag": posFields["Tag"],
                                "Score": posFields["Score"],
                                "Val1": posFields["Val1"],
                                "Val2": posFields["Val2"],
                                "Val3": posFields["Val3"],
                                "Val4": posFields["Val4"],
                                "Val5": posFields["Val5"],
                                "Level": posFields["Level"],
                                "PosGenId": positionGeneratorId}}
                objects.update(newPos)
                sentCount += 1
            callback.NewPosition(objects)
            return sentCount

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

                        _, posList, acqNo, declaredCount, availableCount = parsedLine
                        if declaredCount != availableCount:
                            # The camera always pads the line to its maximum object slot count.
                            logger.log(
                                "startSensor",
                                "AcqNo {}: NumberOfObjects={} but {} object block(s) present; extra blocks ignored.".format(
                                    acqNo, declaredCount, availableCount
                                ),
                                success=True,
                            )
                        if acqNo not in acqStrobeDict:
                            logger.log(
                                "startSensor",
                                "AcqNo {} not in strobe buffer; position discarded.".format(acqNo),
                            )
                            continue

                        strobeTime = acqStrobeDict.pop(acqNo)
                        sentCount = sendNewPositions(posList, strobeTime)
                        logger.log(
                            "startSensor",
                            "Sent {} object(s) for AcqNo={} (declared={}) posGenId={} time={}".format(
                                sentCount, acqNo, declaredCount, positionGeneratorId, strobeTime
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
                # 10038 means the socket was already closed by the stop sequence.
                if ex.errno == 10038 or (ex.errno in (10053, 10054, 10058) and not self.isRunning):
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
                    "Invalid text format. Expected 'AcqNo' or 'AcqNo,NumberOfObjects' followed by "
                    "NumberOfObjects blocks of 'X,Y,RZ,Tag,Score,Val1,Val2,Val3,Val4,Val5,Level'.",
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
