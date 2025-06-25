# IMPORTS
from kivy.clock import Clock
from utils.CVUtils import (
    ICON_ENUM,
    RGB_COLORS_ENUM as RGB,
    COLOR_CHANNEL_FORMAT_ENUM as COLOR_FMT,
    CVUtils,
)
from utils.PermissionManager import PermissionManager
from utils.StatisticsManager import StatisticsManager
from utils.PulseExtractor import PPGPulseExtractor
from utils.SettingsManager import SettingsManager
from utils.CVCameraHandler import CVCameraHandler
from utils.FaceDetector import FaceDetector
from utils.MainLayout import MainLayout
from cv2.typing import MatLike
import numpy as np
import time
import cv2
from kivy.core.window import Window
from kivy.uix.image import Image
from kivy.app import App

PREFERRED_ICON_SIZE_PX: int = 100
PREFERRED_WINDOW_SIZE: tuple[int, int] = (606 * 2, 1280 * 2)


class MainApp(App):
    def build(self):
        # android permissions
        self.faceDetector = FaceDetector(
            SettingsManager.HAARCASCADE_FACE_EXTRACTOR,
            SettingsManager.PROCESSING_IMAGE_SIZE,
        )
        self.fingerPulseExtractor = PPGPulseExtractor(
            SettingsManager.PROCESSING_FRAMERATE.value,
            SettingsManager.RECORDING_TIME_SECONDS,
            SettingsManager.PPG_TARGET_CLARITY_THRESHOLD,
            SettingsManager.PROCESSING_IMAGE_SIZE,
            (SettingsManager.MIN_HEARTRATE_BPM, SettingsManager.MAX_HEARTRATE_BPM),
            SettingsManager.PPG_BANDPASS_ORDER,
        )

        self.permissionManager = PermissionManager()
        self.permissionManager.requestPermissions()

        self.statisticsManager = StatisticsManager(100)
        self.faceBoundingBoxes = []
        self.foreheadBoundingBoxes = []
        self.cheekBoundingBoxes = []

        # app layout
        self.layout = MainLayout()

        # my class objects
        self.cvMainCamHandler = CVCameraHandler(
            0, SettingsManager.RECODRING_IMAGE_SIZE, SettingsManager.PREVIEW_FRAMERATE
        )
        self.cvFrontCamHandler = CVCameraHandler(
            1, SettingsManager.RECODRING_IMAGE_SIZE, SettingsManager.PREVIEW_FRAMERATE
        )

        # update loop
        Clock.schedule_interval(self.update, 0)

        Window.size = PREFERRED_WINDOW_SIZE

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
                    SettingsManager.PREVIEW_FRAMERATE.value
                    / SettingsManager.PROCESSING_FRAMERATE.value
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
                    cvCanvas.texture = CVUtils.cvImageToKivyTexture(
                        self.upscalePreview(CVCameraHandler.NOT_AVAILABLE_IMAGE)
                    )
                # remove camera canvas if unavailable
                # self.layout.remove_widget(cvCanvas)
            curentTime = time.time()
            self.statisticsManager.addValue(
                "averageFrametime", curentTime - self.lastTime
            )
            self.lastTime = curentTime

    def previewUpdate(self, cvHandler: CVCameraHandler, cvCanvas: Image):
        # For every frame that is rendered

        image = CVUtils.putBoundingBoxes(
            cvHandler.currentFrame, self.foreheadBoundingBoxes + self.cheekBoundingBoxes
        )
        self.plotHistograms(image)

        self.fingerPulseExtractor.addFrame(cvHandler.currentFrame, COLOR_FMT.RGB)
        if self.fingerPulseExtractor.pulseSignalAvailable:
            self.fingerPulseExtractor.plotPulseWave(image, RGB.MAGENTA)
            bpmText = f"BPM: {self.fingerPulseExtractor.getBPM():.0f}"
            cv2.putText(
                image,
                bpmText,
                (image.shape[1] - len(bpmText) * 40, 50),
                cv2.FONT_HERSHEY_DUPLEX,
                2,
                RGB.BLACK.value,
                thickness=4,
            )

        preview = self.upscalePreview(image)
        self.plotFramesPerSecond(preview)
        self.drawIcons(preview)

        cvCanvas.texture = self.statisticsManager.run(
            "imageToTexture", CVUtils.cvImageToKivyTexture, preview
        )

    def upscalePreview(self, image: MatLike) -> MatLike:
        h, w = image.shape[:2]
        preferredWidth = Window.size[0]
        preferredHeight = int(round(h / w * preferredWidth))
        preview = cv2.resize(image, (preferredWidth, preferredHeight))
        return preview

    def processingUpdate(self, cvHandler: CVCameraHandler):
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
            FaceDetector.extractForeheadBoundingBox(bb) for bb in faceBoundingBoxes
        ]

        cheekBoundingBoxes = [
            FaceDetector.extractCheekBoundingBox(bb) for bb in faceBoundingBoxes
        ]
        return faceBoundingBoxes, foreheadBoundingBoxes, cheekBoundingBoxes

    def plotFramesPerSecond(self, image: MatLike):
        if "averageFrametime" in self.statisticsManager.statistics:
            fpsText = f"FPS: {1 / self.statisticsManager.statistics["averageFrametime"].average:.0f}"
            cv2.putText(
                image,
                fpsText,
                (5, image.shape[0] - 5),
                cv2.FONT_HERSHEY_DUPLEX,
                2,
                RGB.BLACK.value,
                thickness=4,
            )

    def plotHistograms(self, image):
        r, g, b = CVUtils.calcHists(
            image,
            colorFormat=COLOR_FMT.RGB,
        )
        maxValue = max(np.max(r), np.max(g), np.max(b))
        for color, hist in [
            (RGB.RED, r),
            (RGB.GREEN, g),
            (RGB.BLUE, b),
        ]:
            CVUtils.plotData(
                image,
                hist,
                color,
                mutate=True,
                maxValue=maxValue,
                plotCenterOfMass=True,
            )

    def drawIcons(self, image: MatLike):
        d = PREFERRED_ICON_SIZE_PX
        # draw finger indicator:
        fingerIndicatorColor = RGB.GREY
        if not self.fingerPulseExtractor.hasFinger:
            fingerIndicatorColor = RGB.RED
        elif self.fingerPulseExtractor.pulseSignalAvailable:
            fingerIndicatorColor = RGB.GREEN
        elif self.fingerPulseExtractor.requiresRecording() or not all(
            self.fingerPulseExtractor.hasFingerFlagBuffer
        ):
            fingerIndicatorColor = RGB.BLUE
            CVUtils.putProgressRect(
                image,
                (0, 0, d, d),
                len(self.fingerPulseExtractor.sampleBuffer)
                / self.fingerPulseExtractor.expectedFramesCount,
                RGB.GREEN,
            )

        CVUtils.putIcon(
            image,
            ICON_ENUM.TOUCH,
            (0, 0),
            (d, d),
            fingerIndicatorColor,
            COLOR_FMT.BGRA,
        )

        # draw face indicator
        faceIndicatorColor = RGB.GREY
        if len(self.faceBoundingBoxes) == 1:
            if self.fingerPulseExtractor.pulseSignalAvailable:
                faceIndicatorColor = RGB.GREEN
            else:
                faceIndicatorColor = RGB.BLUE
        else:
            faceIndicatorColor = RGB.RED

        CVUtils.putIcon(
            image,
            ICON_ENUM.FACE,
            (d, 0),
            (d, d),
            faceIndicatorColor,
            COLOR_FMT.BGRA,
        )


def main():
    MainApp().run()


if __name__ == "__main__":
    main()
