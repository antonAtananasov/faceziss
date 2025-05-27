import kivy
from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.widget import Widget
from kivy.graphics.texture import Texture
from kivy.clock import Clock
from kivy.properties import (
    ObjectProperty,
    ListProperty,
    BooleanProperty,
    NumericProperty,
)
import cv2
import numpy as np
from jnius import autoclass, PythonJavaClass, java_method, cast
from android.runnable import run_on_ui_thread

PERMISSIONS_LIST = []
if kivy.platform == "android":
    from android.permissions import (  # pylint: disable=import-error # type: ignore
        request_permissions,
        Permission,
        check_permission,
    )

    PERMISSIONS_LIST = [Permission.CAMERA,Permission.READ_EXTERNAL_STORAGE]

JniusCameraClass = autoclass("android.hardware.Camera")
PythonActivity = autoclass("org.kivy.android.PythonActivity")
SurfaceView = autoclass("android.view.SurfaceView")
LayoutParams = autoclass("android.view.ViewGroup$LayoutParams")

activity = PythonActivity.mActivity

# Get the camera service
Context = autoclass('android.content.Context')
camera_service = activity.getSystemService(Context.CAMERA_SERVICE)

# CameraManager is returned directly from getSystemService
CameraManager = autoclass('android.hardware.camera2.CameraManager')
camera_manager = camera_service
CameraCharacteristics = autoclass('android.hardware.camera2.CameraCharacteristics')
CameraMetadata = autoclass('android.hardware.camera2.CameraMetadata')

def listCamCapabilities():
    camera_id_list = camera_manager.getCameraIdList()

    for camera_id in camera_id_list:
        print(f"\nCamera ID: {camera_id}")
        characteristics = camera_manager.getCameraCharacteristics(camera_id)
        
        # Determine if this is a logical multi-camera
        try:
            physical_ids = characteristics.get(CameraCharacteristics.LOGICAL_MULTI_CAMERA_PHYSICAL_IDS)
            
            if physical_ids:
                physical_ids_array = physical_ids.toArray()
                if len(physical_ids_array) > 1:
                    print("This is a logical multi-camera with physical IDs:")
                    for pid in physical_ids_array:
                        print(f"  - {pid}")
                else:
                    print("Single physical camera.")
            else:
                print("No physical camera IDs found (not a logical multi-camera).")
        except Exception as e:
            print(f"Error checking physical cameras: {e}")

    for camera_id in camera_id_list:
        print(f"\nCamera ID: {camera_id}")
        characteristics = camera_manager.getCameraCharacteristics(camera_id)

        # Get available capabilities
        capabilities = characteristics.get(CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES)

        # Check if LOGICAL_MULTI_CAMERA capability is present
        logical_multi_camera_cap = CameraMetadata.REQUEST_AVAILABLE_CAPABILITIES_LOGICAL_MULTI_CAMERA

        if capabilities is not None:
            capabilities_array = capabilities  # This is a Java int[]
            is_logical = False
            for i in range(len(capabilities_array)):
                if capabilities_array[i] == logical_multi_camera_cap:
                    is_logical = True
                    break

            if is_logical:
                print("✅ Logical multi-camera supported!")
            else:
                print("❌ Logical multi-camera NOT supported.")
        else:
            print("Could not retrieve capabilities.")

class PreviewCallback(PythonJavaClass):

    __javainterfaces__ = ("android.hardware.Camera$PreviewCallback",)

    def __init__(self, callback):
        super(PreviewCallback, self).__init__()
        self.callback = callback


def requestPermissions(permissionsList: list = PERMISSIONS_LIST):
    print("Requesting permissions:", permissionsList)
    if kivy.platform == "android":
        request_permissions(permissionsList)


def checkPermissions(permissionsList: list = PERMISSIONS_LIST):
    hasPermissions = []
    if kivy.platform == "android":
        hasPermissions = [check_permission(p) for p in permissionsList]
        if not all(hasPermissions):
            print("Requesting one or more permissions failed")
    return hasPermissions


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


class AndroidWidgetHolder(Widget):
    view = ObjectProperty(allownone=True)

    def __init__(self, **kwargs):
        self._old_view = None
        self.pos = kwargs["pos"]
        from kivy.core.window import Window

        self._window = Window
        kwargs["size_hint"] = (None, None)
        super(AndroidWidgetHolder, self).__init__(**kwargs)

    def on_view(self, instance, view):
        activity = PythonActivity.mActivity
        activity.addContentView(view, LayoutParams(*self.size))
        view.setZOrderOnTop(True)
        view.setX(self.x + self.pos[0])
        view.setY(self._window.height - (self.y + self.pos[1]) - self.height)


class AndroidCamera(Widget):
    __events__ = ("on_preview_frame",)

    def __init__(self, cameraIndex=0, **kwargs):
        self.index = cameraIndex
        self._holder = None
        self._android_camera = None
        super(AndroidCamera, self).__init__(**kwargs)
        self._holder = AndroidWidgetHolder(size=self.size, pos=kwargs["pos"])
        self.add_widget(self._holder)
        self.start()

    @run_on_ui_thread
    def stop(self):
        if self._android_camera is None:
            return
        self._android_camera.setPreviewCallback(None)
        self._android_camera.release()
        self._android_camera = None
        self._holder.view = None

    @run_on_ui_thread
    def start(self):

        if self._android_camera is not None:
            return

        self._android_camera = JniusCameraClass.open(self.index)

        self._android_surface = SurfaceView(PythonActivity.mActivity)
        surface_holder = self._android_surface.getHolder()

        self._android_surface_cb = SurfaceHolderCallback(self._on_surface_changed)
        surface_holder.addCallback(self._android_surface_cb)

        self._holder.view = self._android_surface
        # self._holder2.view = self._android_surface

    def _on_surface_changed(self, fmt, width, height):

        params = self._android_camera.getParameters()
        params.setPreviewSize(width, height)
        self._android_camera.setParameters(params)
        self._previewCallback = PreviewCallback(self._on_preview_frame)

        self._android_camera.setPreviewCallbackWithBuffer(self._previewCallback)
        self._android_camera.setPreviewDisplay(self._android_surface.getHolder())
        self._android_camera.startPreview()

    def _on_preview_frame(self, camera, data):
        self.dispatch("on_preview_frame", camera, data)
        self._android_camera.addCallbackBuffer(data)

    def on_preview_frame(self, camera, data):
        print(camera, data)

    def on_size(self, instance, size):
        if self._holder:
            self._holder.size = size

    def on_pos(self, instance, _):
        if self._holder:
            pass


class MyCVHandler:
    def __init__(self, cameraIndex: int):
        self.cvCapture = cv2.VideoCapture(cameraIndex)

        self.notAvailableImage = np.zeros((240, 320, 4), np.uint8)
        self.notAvailableImage[:] = (255, 0, 255, 255)
        cv2.putText(
            self.notAvailableImage,
            "Not available",
            (0, 120),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
        )

    def update(self) -> bool:
        # load image from cam
        available, frame = self.cvCapture.read()
        self.available = available

        self.currentFrame = frame if self.available else self.notAvailableImage

        return self.available

    def cvImageToKivyTexture(self, cvImage) -> Texture:
        # convert it to texture
        npImage = (
            np.append(
                cvImage,
                np.ones((cvImage.shape[0], cvImage.shape[1], 1), np.uint8) * 255,
                axis=2,
            )
            if cvImage.shape[2] == 3
            else cvImage
        )
        buf1 = cv2.flip(npImage, 0)
        buf = buf1.tobytes()
        cvTexture = Texture.create(
            size=(npImage.shape[1], npImage.shape[0]), colorfmt="rgba"
        )

        cvTexture.blit_buffer(buf, colorfmt="rgba", bufferfmt="ubyte")

        return cvTexture


class MyBoxLayout(BoxLayout):
    camera_size = ListProperty([640, 480])

    def __init__(self, **kwargs):
        super(MyBoxLayout, self).__init__(**kwargs)
        self.orientation = "vertical"

        self.cvMainCamCanvas = Image()
        self.add_widget(self.cvMainCamCanvas)

        self.cvFrontCamCanvas = Image()
        self.add_widget(self.cvFrontCamCanvas)

        self._camera = AndroidCamera(
            cameraIndex=0, size=self.camera_size, size_hint=(None, None), pos=(100, 200)
        )
        self.add_widget(self._camera)

        self._camera2 = AndroidCamera(
            cameraIndex=1, size=self.camera_size, size_hint=(None, None), pos=(100, 450)
        )
        self.add_widget(self._camera2)

        self._camera.stop()
        self._camera2.stop()

        # create widget
        button1 = Button(text="Click Me!")
        # bind widget properties if needed
        button1.bind(on_press=self.on_button_press)
        # place widget on layout
        self.add_widget(button1)

    def on_button_press(self, instance):
        app = App.get_running_app()

        if not hasattr(self, "testcam"):
            self.testcam = 1
        else:
            self.testcam += 1

        if self.testcam == 0:
            self._camera.stop()
            self._camera2.stop()
        elif self.testcam % 2 == 1:
            self._camera2.stop()
            self._camera.start()
        elif self.testcam % 2 == 0:
            self._camera.stop()
            self._camera2.start()

        for attr in dir(CameraManager):
            try:
                print(attr, getattr(CameraManager, attr))
            except:
                print(attr, "?")

        listCamCapabilities()


class MyApp(App):
    def build(self):
        # app layout
        self.layout = MyBoxLayout()

        # my class objects
        self.settings = MySettings()
        self.cvMainCamHandler = MyCVHandler(0)
        self.cvFrontCamHandler = MyCVHandler(1)
        # self.jniusCameras = [JniusCameraClass.open(0)]

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


if __name__ == "__main__":
    requestPermissions()
    MyApp().run()
