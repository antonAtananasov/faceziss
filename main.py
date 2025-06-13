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


RECODRING_IMAGE_SIZE: RESOLUTIONS_ENUM = RESOLUTIONS_ENUM.LOW
PROCESSING_IMAGE_SIZE: RESOLUTIONS_ENUM = RESOLUTIONS_ENUM.LOWEST
HAARCASCADE_FACE_EXTRACTOR: HAARCASCADE_FACE_EXTRACTORS_ENUM = (
    HAARCASCADE_FACE_EXTRACTORS_ENUM.FRONTALFACE_ALT
)
RECORDING_FRAMERATE: FRAMERATES_ENUM = FRAMERATES_ENUM.HIGH
PROCESSING_FRAMERATE: FRAMERATES_ENUM = FRAMERATES_ENUM.LOWEST

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
        Clock.schedule_interval(self.update, 1 / RECORDING_FRAMERATE.value)

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
                if (
                    framesSkipped >= framesToSkip
                ) or framesToSkip <= 1:
                    self.boundingBoxes = self.faceDetector.extractFaceBoundingBoxes(
                        cvHandler.currentFrame
                    )
                    setattr(self, frameSkipFlag, 0)
                else:
                    setattr(self, frameSkipFlag, framesSkipped+1)

                image = MyFaceDetector.putBoundingBoxes(
                    cvHandler.currentFrame, getattr(self, "boundingBoxes", [])
                )
                cvCanvas.texture = cvHandler.cvImageToKivyTexture(image)
            else:
                # suppres updates if handler not active
                blockflag = f"block_{id(cvHandler)}_update"
                if not hasattr(self, blockflag):
                    setattr(self, blockflag, True)
                    cvCanvas.texture = MyCVHandler.NOT_AVAILABLE_TEXTURE
                # remove camera canvas if unavailable
                # self.layout.remove_widget(cvCanvas)


def main():
    FacezissApp().run()


if __name__ == "__main__":
    main()
