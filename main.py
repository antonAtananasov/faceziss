# IMPORTS
import kivy
from kivy.app import App
from kivy.core.window import Window
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.widget import Widget
from kivy.clock import Clock
from kivy.properties import (
    ObjectProperty,
    ListProperty,
    BooleanProperty,
    NumericProperty,
)

if kivy.platform == "android":
    from utils.JNIUtils import (
        FrameCallback,
        JniusPythonActivityContext,
        LogicalCameraToRGB,
        TonzissCameraChecker,
    )
from utils.MyCVUtils import (
    RESOLUTIONS_ENUM as RESOLUTION,
    HAARCASCADE_FACE_EXTRACTORS_ENUM as HAARCASCADES,
    FRAMERATES_ENUM as FPS,
    RGB_COLORS_ENUM as RGB,
    COLOR_CHANNEL_FORMAT_ENUM as COLOR_FMT,
    MyCVUtils,
)
from utils.MyCVHandler import MyCVHandler
from utils.MyFaceDetector import MyFaceDetector
from utils.MyPulseExtractor import MyPulseExtractor
from utils.PermissionUtils import MyPermissionManager
from utils.MyStatisticsManager import MyStatistics
import numpy as np
import time
import cv2


# SETTINGS:
RECODRING_IMAGE_SIZE: RESOLUTION = RESOLUTION.LOW
PROCESSING_IMAGE_SIZE: RESOLUTION = RESOLUTION.LOWEST
HAARCASCADE_FACE_EXTRACTOR: HAARCASCADES = HAARCASCADES.FRONTALFACE_DEFAULT
PREVIEW_FRAMERATE: FPS = FPS.LOW
PROCESSING_FRAMERATE: FPS = FPS.LOW
RECORDING_TIME_SECONDS: float = 3
FINGER_MOVEMENT_THRESHOLD: float = 3
MAX_HEARTRATE_BPM: float = 120


# LAYOUTS
class MyHorizontalBoxLayout(BoxLayout):
    def __init__(self, elements: list, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "horizontal"
        for element in elements:
            self.add_widget(element)


class MainBoxLayout(BoxLayout):
    camera_size = ListProperty(list(RECODRING_IMAGE_SIZE.value))

    def __init__(self, **kwargs):
        super(MainBoxLayout, self).__init__(**kwargs)
        self.orientation = "vertical"

        self.cvMainCamCanvas = Image()
        self.add_widget(self.cvMainCamCanvas)

        self.cvFrontCamCanvas = Image()
        self.add_widget(self.cvFrontCamCanvas)

        # create widget
        button1 = Button(text="Click Me!")
        mainApp: FacezissApp = App.get_running_app()
        button1.bind(
            on_press=lambda instance: print(
                np.array(mainApp.fingerPulseExtractor.sampleBuffer),
                mainApp.fingerPulseExtractor.averageSamplingRate,
                mainApp.fingerPulseExtractor.window,
            )
        )

        button2 = Button(text="^")
        button3 = Button(text="v")
        button2.bind(
            on_press=lambda instance: mainApp.cvMainCamHandler.increaseExposure()
        )
        button3.bind(
            on_press=lambda instance: mainApp.cvMainCamHandler.decreaseExposure()
        )

        self.add_widget(MyHorizontalBoxLayout([button1, button2, button3]))

    def on_button_press(self, instance):
        # app = App.get_running_app()
        tonzissCameraChecker = TonzissCameraChecker(JniusPythonActivityContext)
        logicalCameraToRGB = LogicalCameraToRGB(
            JniusPythonActivityContext,
            RECODRING_IMAGE_SIZE.value[0],
            RECODRING_IMAGE_SIZE.value[1],
            FrameCallback(lambda image: print(image)),
        )
        cameraIds = tonzissCameraChecker.getCameraIdList()
        simultaneousCameraCombinations = (
            tonzissCameraChecker.getSimultaneousCameraCombinationIds()
        )
        print("Camera Id List:", cameraIds)
        print("Multi-Cameras:", simultaneousCameraCombinations)
        # for cameraId in cameraIds:
        #     print(f"Camera {cameraId} characteristics:")
        #     pprintObject(tonzissCameraChecker.getCameraCharacteristics(cameraId), 0)


class FacezissApp(App):
    def build(self):
        # android permissions
        self.faceDetector = MyFaceDetector(
            HAARCASCADE_FACE_EXTRACTOR, PROCESSING_IMAGE_SIZE
        )
        self.fingerPulseExtractor = MyPulseExtractor(
            PROCESSING_FRAMERATE.value,
            RECORDING_TIME_SECONDS,
            FINGER_MOVEMENT_THRESHOLD,
            PROCESSING_IMAGE_SIZE,
            MAX_HEARTRATE_BPM,
        )
        self.cheekPulseExtractor = MyPulseExtractor(
            PROCESSING_FRAMERATE.value,
            RECORDING_TIME_SECONDS,
            FINGER_MOVEMENT_THRESHOLD,
            PROCESSING_IMAGE_SIZE,
            MAX_HEARTRATE_BPM,
        )
        self.permissionManager = MyPermissionManager()
        self.permissionManager.requestPermissions()

        self.statisticsManager = MyStatistics(100)
        self.faceBoundingBoxes = []
        self.foreheadBoundingBoxes = []
        self.cheekBoundingBoxes = []

        # app layout
        self.layout = MainBoxLayout()

        # my class objects
        self.cvMainCamHandler = MyCVHandler(0, RECODRING_IMAGE_SIZE, PREVIEW_FRAMERATE)
        self.cvFrontCamHandler = MyCVHandler(1, RECODRING_IMAGE_SIZE, PREVIEW_FRAMERATE)

        # update loop
        Clock.schedule_interval(self.update, 0)

        Window.size = (606, 1280)

        self.lastTime = time.time()
        return self.layout

    def update(self, dt):
        for cvHandler, cvCanvas in (
            (self.cvMainCamHandler, self.layout.cvMainCamCanvas),
            (self.cvFrontCamHandler, self.layout.cvFrontCamCanvas),
        ):
            # update camera
            if cvHandler.update():
                framesToSkip = round(
                    PREVIEW_FRAMERATE.value / PROCESSING_FRAMERATE.value
                )
                frameSkipFlag = f"frameskip_{id(cvHandler)}_{framesToSkip}"
                framesSkipped = getattr(self, frameSkipFlag, float("inf"))

                if (framesSkipped >= framesToSkip) or framesToSkip <= 1:
                    self.processingUpdate(cvHandler)

                    setattr(self, frameSkipFlag, 0)

                else:
                    setattr(self, frameSkipFlag, framesSkipped + 1)

                self.previewUpdate(cvHandler, cvCanvas)
            else:
                # suppres updates if handler not active
                blockflag = f"block_{id(cvHandler)}_update"
                if not hasattr(self, blockflag):
                    setattr(self, blockflag, True)
                    cvCanvas.texture = MyCVHandler.NOT_AVAILABLE_TEXTURE
                # remove camera canvas if unavailable
                # self.layout.remove_widget(cvCanvas)
            curentTime = time.time()
            self.statisticsManager.newValue(
                "averageFrametime", curentTime - self.lastTime
            )
            self.lastTime = curentTime

    def previewUpdate(self, cvHandler: MyCVHandler, cvCanvas: Image):
        # For every frame that is rendered

        image = MyFaceDetector.putBoundingBoxes(
            cvHandler.currentFrame, self.foreheadBoundingBoxes + self.cheekBoundingBoxes
        )
        self.plotHistograms(image)

        if len(self.cheekBoundingBoxes) == 1:
            self.cheekPulseExtractor.addFrame(
                MyCVUtils.cropToRect(
                    cvHandler.currentFrame, self.cheekBoundingBoxes[0]
                ),
                COLOR_FMT.RGB,
                False,
            )
        else:
            self.cheekPulseExtractor.reset()
            
        if self.cheekPulseExtractor.pulseSignalAvailable:
            # TODO: implement pulse extraction with evm in realtime 
            pass
        else:
            print(
                np.std(self.cheekPulseExtractor.sampleBuffer),
                f"{self.cheekPulseExtractor.window}/{self.cheekPulseExtractor.recordingTimeSeconds}",
                f"{len(self.cheekPulseExtractor.sampleBuffer)}",
            )


        self.fingerPulseExtractor.addFrame(cvHandler.currentFrame, COLOR_FMT.RGB)
        if self.fingerPulseExtractor.pulseSignalAvailable:
            self.plotPulseWave(image, self.fingerPulseExtractor, RGB.MAGENTA)


        self.plotFramesPerSecond(image)

        cvCanvas.texture = self.statisticsManager.run(
            "imageToTexture", cvHandler.cvImageToKivyTexture, image
        )

    def processingUpdate(self, cvHandler):
        # For slower processes that may skip frames in between

        face, forehead, cheek = self.findFaces(cvHandler.currentFrame)
        self.faceBoundingBoxes = face
        self.foreheadBoundingBoxes = forehead
        self.cheekBoundingBoxes = cheek

    def findFaces(self, image):
        faceBoundingBoxes = self.statisticsManager.run(
            "extractor",
            self.faceDetector.extractFaceBoundingBoxes,
            image,
        )

        foreheadBoundingBoxes = [
            MyFaceDetector.faceBoundingToForeheadBounding(bb)
            for bb in faceBoundingBoxes
        ]

        cheekBoundingBoxes = [
            MyFaceDetector.faceBoundingToCheekBounding(bb) for bb in faceBoundingBoxes
        ]
        return faceBoundingBoxes, foreheadBoundingBoxes, cheekBoundingBoxes

    def plotFramesPerSecond(self, image):
        if "averageFrametime" in self.statisticsManager.statistics:
            cv2.putText(
                image,
                str(
                    round(
                        1
                        / self.statisticsManager.statistics["averageFrametime"].average
                    )
                ),
                (5, RECODRING_IMAGE_SIZE.value[1] - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 0, 0),
            )

    def plotHistograms(self, image):
        r, g, b = MyPulseExtractor.calcHists(
            image,
            colorFormat=COLOR_FMT.RGB,
        )
        maxValue = max(np.max(r), np.max(g), np.max(b))
        for color, hist in [
            (RGB.RED, r),
            (RGB.GREEN, g),
            (RGB.BLUE, b),
        ]:
            MyCVHandler.plotData(
                image,
                hist,
                color,
                mutate=True,
                maxValue=maxValue,
                plotCenterOfMass=True,
            )

    def plotPulseWave(self, image, pulseExtractor: MyPulseExtractor, color: RGB):
        MyCVHandler.plotData(
            image,
            pulseExtractor.sampleBuffer,
            color,
            plotCenterOfMass=False,
            mutate=True,
        )
        _, t, a = pulseExtractor.getPulsePeaks()
        for i in range(len(t)):
            p = (
                t[i] / pulseExtractor.window * image.shape[1],
                image.shape[0]
                - np.interp(
                    a[i],
                    [
                        np.min(pulseExtractor.sampleBuffer),
                        np.max(pulseExtractor.sampleBuffer),
                    ],
                    [0, image.shape[0]],
                ),
            )
            cv2.circle(
                image,
                np.int32(p),
                5,
                color.value,
                cv2.FILLED,
            )


def main():
    FacezissApp().run()


if __name__ == "__main__":
    main()
