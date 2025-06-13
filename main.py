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
from utils.MyCVUtils import MyCVHandler
from utils.PermissionUtils import MyPermissionManager


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
    def __init__(self, fps: float = 60):
        self.fps = fps


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
    camera_size = ListProperty([640, 480])

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
            640,
            480,
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


class MyApp(App):
    def build(self):
        # android permissions
        self.permissionManager = MyPermissionManager()
        self.permissionManager.requestPermissions()

        # app layout
        self.layout = MyBoxLayout()

        # my class objects
        self.settings = MySettings()
        self.cvMainCamHandler = MyCVHandler(0)
        self.cvFrontCamHandler = MyCVHandler(1)

        # update loop
        Clock.schedule_interval(self.update, 1 / self.settings.fps)

        return self.layout

    def update(self, dt):
        for cvHandler, cvCanvas in (
            (self.cvMainCamHandler, self.layout.cvMainCamCanvas),
            (self.cvFrontCamHandler, self.layout.cvFrontCamCanvas),
        ):
            # update camera
            if cvHandler.update() or True:
                cvCanvas.texture = cvHandler.cvImageToKivyTexture(
                    cvHandler.currentFrame
                )
            else:
                # remove camera canvas if unavailable
                self.layout.remove_widget(cvCanvas)


def main():
    MyApp().run()


if __name__ == "__main__":
    main()
