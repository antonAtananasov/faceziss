import kivy
from kivy.app import App
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
    MyCVHandler,
    MyFaceDetector,
    RESOLUTIONS_ENUM,
    HAARCASCADE_FACE_EXTRACTORS_ENUM,
    FRAMERATES_ENUM,
)
from utils.PermissionUtils import MyPermissionManager
from utils.MyStatisticsManager import MyStatistics
import time
import cv2


RECODRING_IMAGE_SIZE: RESOLUTIONS_ENUM = RESOLUTIONS_ENUM.LOW
PROCESSING_IMAGE_SIZE: RESOLUTIONS_ENUM = RESOLUTIONS_ENUM.LOWEST
HAARCASCADE_FACE_EXTRACTOR: HAARCASCADE_FACE_EXTRACTORS_ENUM = (
    HAARCASCADE_FACE_EXTRACTORS_ENUM.FRONTALFACE_DEFAULT
)
RECORDING_FRAMERATE: FRAMERATES_ENUM = FRAMERATES_ENUM.MEDIUM
PROCESSING_FRAMERATE: FRAMERATES_ENUM = FRAMERATES_ENUM.MEDIUM

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
        self.fps = RECORDING_FRAMERATE.value


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


class MyBoxLayout(BoxLayout):
    camera_size = ListProperty(list(RECODRING_IMAGE_SIZE.value))

    def __init__(self, **kwargs):
        super(MyBoxLayout, self).__init__(**kwargs)
        self.orientation = "vertical"

        self.cvMainCamCanvas = Image()
        self.add_widget(self.cvMainCamCanvas)

        self.cvFrontCamCanvas = Image()
        self.add_widget(self.cvFrontCamCanvas)

        # create widget
        button1 = Button(text="Click Me!")
        # bind widget properties if needed
        button1.bind(on_press=self.on_button_press)
        # place widget on layout
        self.add_widget(button1)

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
        self.permissionManager = MyPermissionManager()
        self.permissionManager.requestPermissions()

        self.statisticsManager = MyStatistics(100)

        # app layout
        self.layout = MyBoxLayout()

        # my class objects
        self.settings = MySettings()
        self.cvMainCamHandler = MyCVHandler(
            0, RECODRING_IMAGE_SIZE, RECORDING_FRAMERATE
        )
        self.cvFrontCamHandler = MyCVHandler(
            1, RECODRING_IMAGE_SIZE, RECORDING_FRAMERATE
        )

        # update loop
        Clock.schedule_interval(self.update, 0)
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
                    RECORDING_FRAMERATE.value / PROCESSING_FRAMERATE.value
                )
                frameSkipFlag = f"frameskip_{id(cvHandler)}_{framesToSkip}"
                framesSkipped = getattr(self, frameSkipFlag, float("inf"))

                if (framesSkipped >= framesToSkip) or framesToSkip <= 1:
                    self.boundingBoxes = self.statisticsManager.run(
                        "extractor",
                        self.faceDetector.extractFaceBoundingBoxes,
                        cvHandler.currentFrame,
                    )

                    self.boundingBoxes += [
                        MyFaceDetector.faceBoundingToForeheadBounding(bb)
                        for bb in self.boundingBoxes
                    ] + [
                        MyFaceDetector.faceBoundingToCheekBounding(bb)
                        for bb in self.boundingBoxes
                    ]

                    setattr(self, frameSkipFlag, 0)

                else:
                    setattr(self, frameSkipFlag, framesSkipped + 1)

                image = MyFaceDetector.putBoundingBoxes(
                    cvHandler.currentFrame, getattr(self, "boundingBoxes", [])
                )
                if "averageFrametime" in self.statisticsManager.statistics:
                    cv2.putText(
                        image,
                        str(
                            round(
                                1
                                / self.statisticsManager.statistics[
                                    "averageFrametime"
                                ].average
                            )
                        ),
                        (5, RECODRING_IMAGE_SIZE.value[1] - 5),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1,
                        (0, 0, 0),
                    )
                cvCanvas.texture = self.statisticsManager.run(
                    "imageToTexture", cvHandler.cvImageToKivyTexture, image
                )
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


def main():
    FacezissApp().run()


if __name__ == "__main__":
    main()
