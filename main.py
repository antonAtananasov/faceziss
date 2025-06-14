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
from jnius import autoclass, PythonJavaClass, java_method, cast
from utils.MyCVUtils import (
    RESOLUTIONS_ENUM as RESOLUTION,
    HAARCASCADE_FACE_EXTRACTORS_ENUM as HAARCASCADES,
    FRAMERATES_ENUM as FPS,
    RGB_COLORS_ENUM as RGB,
    COLOR_CHANNEL_FORMAT_ENUM as COLOR_FMT,
)
from utils.MyCVHandler import MyCVHandler
from utils.MyFaceDetector import MyFaceDetector
from utils.MyFingerPulseExtractor import MyFingerPulseExtractor
from utils.PermissionUtils import MyPermissionManager
from utils.MyStatisticsManager import MyStatistics
import numpy as np
import time
import cv2


# Settings:
RECODRING_IMAGE_SIZE: RESOLUTION = RESOLUTION.LOW
PROCESSING_IMAGE_SIZE: RESOLUTION = RESOLUTION.LOWEST
HAARCASCADE_FACE_EXTRACTOR: HAARCASCADES = HAARCASCADES.FRONTALFACE_DEFAULT
PREVIEW_FRAMERATE: FPS = FPS.LOW
PROCESSING_FRAMERATE: FPS = FPS.LOW
RECORDING_TIME_SECONDS: float = 3
FINGER_MOVEMENT_THRESHOLD: float = 3
MAX_HEARTRATE_BPM: float = 120

# JNI
if kivy.platform == "android":
    TonzissCameraChecker = autoclass("javasrc.faceziss.TonzissCameraChecker")
    LogicalCameraToRGB = autoclass("javasrc.faceziss.LogicalCameraToRGB")
    JniusContentContextClass = autoclass("android.content.Context")
    JniusPythonActivityClass = autoclass("org.kivy.android.PythonActivity")
    JniusPythonActivityContext = JniusPythonActivityClass.mActivity


class PreviewCallback(PythonJavaClass):

    __javainterfaces__ = ("android.hardware.Camera$PreviewCallback",)

    def __init__(self, callback):
        super(PreviewCallback, self).__init__()
        self.callback = callback


class FrameCallback(PythonJavaClass):

    __javainterfaces__ = ("javasrc.faceziss.LogicalCameraToRGB$FrameCallback",)

    def __init__(self, callback):
        super(FrameCallback, self).__init__()
        self.callback = callback


class MySettings:
    def __init__(self):
        self.fps = PREVIEW_FRAMERATE.value


class PreviewCallback(PythonJavaClass):

    __javainterfaces__ = ("android.hardware.Camera$PreviewCallback",)

    def __init__(self, callback):
        super(PreviewCallback, self).__init__()
        self.callback = callback


class SurfaceHolderCallback(PythonJavaClass):
    __javainterfaces__ = ("android.view.SurfaceHolder$Callback",)

    def __init__(self, callback):
        super(SurfaceHolderCallback, self).__init__()
        self.callback = callback

    @java_method("(Landroid/view/SurfaceHolder;III)V")
    def surfaceChanged(self, surface, fmt, width, height):
        self.callback(fmt, width, height)


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
                np.array(mainApp.fingerPulseExtractor.centerOfMassesBuffer),
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
        self.fingerPulseExtractor = MyFingerPulseExtractor(
            PROCESSING_FRAMERATE.value,
            RECORDING_TIME_SECONDS,
            FINGER_MOVEMENT_THRESHOLD,
            PROCESSING_IMAGE_SIZE,
            MAX_HEARTRATE_BPM,
        )
        self.permissionManager = MyPermissionManager()
        self.permissionManager.requestPermissions()

        self.statisticsManager = MyStatistics(100)

        # app layout
        self.layout = MainBoxLayout()

        # my class objects
        self.settings = MySettings()
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

    def previewUpdate(self, cvHandler, cvCanvas):
        image = MyFaceDetector.putBoundingBoxes(
            cvHandler.currentFrame, getattr(self, "boundingBoxes", [])
        )
        self.plotHistograms(image)

        self.fingerPulseExtractor.addFrame(
            cvHandler.currentFrame, COLOR_FMT.RGB_AUTO_ALPHA
        )
        if self.fingerPulseExtractor.pulseSignalAvailable:
            self.plotPulseWave(image)
        else:
            print(np.std(self.fingerPulseExtractor.centerOfMassesBuffer))

        self.plotFramesPerSecond(image)

        cvCanvas.texture = self.statisticsManager.run(
            "imageToTexture", cvHandler.cvImageToKivyTexture, image
        )

    def processingUpdate(self, cvHandler):
        self.boundingBoxes = self.findFaces(cvHandler.currentFrame)

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
        return faceBoundingBoxes + foreheadBoundingBoxes + cheekBoundingBoxes

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
        r, g, b = MyFingerPulseExtractor.calcHists(
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

    def plotPulseWave(self, image):
        MyCVHandler.plotData(
            image,
            self.fingerPulseExtractor.centerOfMassesBuffer,
            RGB.MAGENTA,
            plotCenterOfMass=False,
            mutate=True,
        )
        _, t, a = self.fingerPulseExtractor.getPulsePeaks()
        for i in range(len(t)):
            p = (
                t[i] / self.fingerPulseExtractor.window * image.shape[1],
                image.shape[0]
                - np.interp(
                    a[i],
                    [
                        np.min(self.fingerPulseExtractor.centerOfMassesBuffer),
                        np.max(self.fingerPulseExtractor.centerOfMassesBuffer),
                    ],
                    [0, image.shape[0]],
                ),
            )
            cv2.circle(
                image,
                np.int32(p),
                5,
                RGB.MAGENTA.value,
                cv2.FILLED,
            )
        print(round(self.fingerPulseExtractor.getBpm()))


def main():
    FacezissApp().run()


if __name__ == "__main__":
    main()
