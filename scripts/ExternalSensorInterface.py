

import threading
import time


class SensorInfo:
    name = "External sensor"
    description = "External sensor interfaces description"
    author = "PMTW developer"
    version = "1.0"
    sensorIdNameMapDict = {}  # 'sensorId': 'sensorName' # - stores the relationship between Id and name of used external sensors
    sensorConfigurationDict = {}  # 'sensorId': 'configInfo' # - stores the configuration info string of all used external sensors
    posGenConfigurationDict = {}  # 'posGenId': 'posGenConfigInfo' # - stores the configuration info string of all used position generators
    posGenSensorMapDict = {}  # 'posGenId': 'sensorId'
    # - stores the relationship between all used position generator Id and all used external sensor Id
    posGenObjectMapDict = {}  # 'posGenId': 'objectName' # - stores the relationship between all used position generator Id and object names

    def registerLogCallback(self, logCallBackFunc):
        self.fLogCallback = logCallBackFunc
        self.sensorIdNameMapDict.clear()
        self.sensorConfigurationDict.clear()
        self.posGenConfigurationDict.clear()
        self.posGenSensorMapDict.clear()
        self.posGenObjectMapDict.clear()
        # users can use the logCallBackFunc to show python log in PMTW with the following format:
        #   log = {'LogLevel': 0,'Log': 'python log string'}
        #   self.fLogCallback.ShowPythonLog(log)

    def initializeSensorMap(self, sensorId, sensorName):
        self.sensorIdNameMapDict[sensorId] = sensorName


class SensorConfig(SensorInfo):
    def configureSensor(self, sensorId):
        # users should implement the configuration logic in their class. The content must contain the following parts:
        # Step 1: if configure for the first time, skip step 1.
        #         Otherwise, find the configurationInfo string by self.sensorConfigurationDict[sensorId]
        #         and analyze it to get the configuration setting from last time.
        # Step 2: configuration logic defined by users.
        # Step 3: parse the configuration data into one string and update it in self.sensorConfigurationDict[sensorId].
        pass

    def getSensorInfo(self):
        return self.name, self.author, self.version, self.description

    def loadSensor(self, sensorId, configurationInfo):
        self.sensorConfigurationDict[sensorId] = configurationInfo

    def saveSensor(self, sensorId):
        return self.sensorConfigurationDict[sensorId]


class PositionGenerator(SensorConfig, SensorInfo):
    def initializePosGenRelatedMap(self, sensorId, posGenId, objectName):
        self.posGenSensorMapDict[posGenId] = sensorId
        self.posGenObjectMapDict[posGenId] = objectName

    def configurePosGen(self, posGenId):
        # users should implement the position generator configuration logic in their class. The content must contain the following parts:
        # Step 1: if configure for the first time, skip step 1.
        #         Otherwise, find the configurationInfo string by self.posGenConfigurationDict[posGenId]
        #         and analyze it to get the configuration setting from last time.
        # Step 2: configuration logic defined by users.
        # Step 3: parse the configuration data into one string and update it in self.posGenConfigurationDict[posGenId].
        pass

    def loadPosGen(self, posGenId, positionGeneratorInfo):
        self.posGenConfigurationDict[posGenId] = positionGeneratorInfo

    def savePosGen(self, posGenId):
        return self.posGenConfigurationDict[posGenId]


class SensorRuntime(PositionGenerator, SensorConfig, SensorInfo):
    recipeStatus = 0
    monitorThread: "StoppableThread | None" = None

    def startSensor(self, callBackFunc):
        # users should implement the start logic in their class. The content must contain the following parts:
        # Step 1: call classname.monitorRecipeStatus(self, callBackFunc) to monitor the recipe status running in PMTW.
        # Step 2: start logic defined by users. For each sensor, a StoppableThread
        #         must be created to generate positions and appended to self.allThreads.
        # Step 3: start all threads in self.allThreads.
        # Step 4: call classname.waitForRecipeStop(self) to wait for the stop signal from PMTW.
        # Step 5: stop all threads in self.allThreads. Note that the stop behavior of startSensor interface should be handled by users here.
        #
        # The following information may be helpful:
        # 1. users can use the following dictionaries to find all information:
        #    self.sensorIdNameMapDict
        #    self.sensorConfigurationDict
        #    self.posGenConfigurationDict
        #    self.posGenSensorMapDict
        #    self.posGenObjectMapDict
        # 2. after the sensor is triggered, users should call callBackFunc.GetStrobeTime() to get the strobe time from PMTW.
        # 3. after position is generated, users should call callBackFunc.NewPosition(pos) to send positions to PMTW.
        # 4. the format of position should be (more details refer to user guide document):
        #    newPos = {'SensorId': sensorId,
        #              'Time': strobeTime,
        #              'key':   {'X': 0.0,
        #                        'Y': 100.0,
        #                        'Z': 5.0,
        #                        'RX': 0.0,
        #                        'RY': 0.0,
        #                        'RZ': 0.0,
        #                        'Tag': 0,
        #                        'Score': 1.0,
        #                        'Val1': 0.0,
        #                        'Val2': 0.0,
        #                        'Val3': 0.0,
        #                        'Val4': 0.0,
        #                        'Val5': 0.0,
        #                        'Level': 2,
        #                        'PosGenId': posGenId}}
        pass

    def stopSensor(self):
        # users should implement the stop logic in their class. If there is no specific logic, the interface can keep empty.
        pass

    def monitorRecipeStatus(self, callBackFunc):
        self.recipeStatus = 1
        self.monitorThread = StoppableThread(target=SensorRuntime.checkRecipeStatus, args=(self, callBackFunc))
        self.monitorThread.start()

    def checkRecipeStatus(self, callBackFunc):
        while True:
            self.recipeStatus = callBackFunc.GetRecipeStatus()
            time.sleep(1)
            if self.recipeStatus == 0:
                break

    def waitForRecipeStop(self):
        while True:
            if self.recipeStatus == 0:
                break
        if self.monitorThread is not None:
            self.monitorThread.stop()


class StoppableThread(threading.Thread):
    # Tool to realize that the threading.Thread could be stopped.
    def __init__(self, target=None, args=(), kwargs=None, daemon=True):
        super(StoppableThread, self).__init__(target=target, args=args, kwargs=kwargs, daemon=daemon)
        self.flag = threading.Event()

    def stop(self):
        self.flag.set()
        if self.is_alive():
            self.join(timeout=2)
