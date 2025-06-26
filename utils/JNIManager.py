from jnius import autoclass, PythonJavaClass, java_method
from utils.SettingsManager import SettingsManager
import kivy

def androidonly(func):
    def wrapper(self, *args, **kwargs):
        if not self.isAndroid:
            print(
                f"Cannot call method {func} on platform other than android. Current platform: {self.platform}"
            )
        else:
            return func(self, *args, **kwargs)
    return wrapper

class JNIManager:
    def __init__(self):
        self.platform = kivy.platform
        self.isAndroid = self.platform == "android"

        # skip rest of setup
        if not self.isAndroid:
            return

        self.PythonActivity = autoclass("org.kivy.android.PythonActivity")
        self.mActivity = self.PythonActivity.mActivity
        self.Context = autoclass("android.content.Context")
        self.CameraManager = self.PythonActivity.mActivity.getSystemService(
            self.Context.CAMERA_SERVICE
        )
        self.CameraCheckerClass = autoclass("utils.java.CameraChecker")
        self.CameraCheckerInstance = self.CameraCheckerClass(self.mActivity)
        self.LogicalCameraToRGBClass = autoclass("utils.java.LogicalCameraToRGB")
        # self.LogicalCameraToRGBInstance = self.LogicalCameraToRGBClass(
        #     self.Context,
        #     SettingsManager.RECODRING_IMAGE_SIZE.value[0],
        #     SettingsManager.RECODRING_IMAGE_SIZE.value[1],
        #     FrameCallback(lambda image: print(image)),
        # ) # jnius.jnius.JavaException: JVM exception occurred: interface utils.java.LogicalCameraToRGB$FrameCallback is not visible from class loader java.lang.IllegalArgumentException 


    @androidonly
    def printLogicalCameraConfigurations(self):
        if not self.isAndroid:
            print(self._generate_cannot_call_method_message())
            return

        cameraIds = self.CameraCheckerInstance.getCameraIdList()
        simultaneousCameraCombinations = (
            self.CameraCheckerInstance.getSimultaneousCameraCombinationIds()
        )
        print("Camera Id List:", cameraIds)
        print("Multi-Cameras:", simultaneousCameraCombinations)


# class PreviewCallback(PythonJavaClass):

#     __javainterfaces__ = ("android.hardware.Camera$PreviewCallback",)

#     def __init__(self, callback):
#         super(PreviewCallback, self).__init__()
#         self.callback = callback


# class FrameCallback(PythonJavaClass):
#     __javainterfaces__ = ("utils.java.LogicalCameraToRGB$FrameCallback",)

#     def __init__(self, callback):
#         super(FrameCallback, self).__init__()
#         self.callback = callback


# class PreviewCallback(PythonJavaClass):

#     __javainterfaces__ = ("android.hardware.Camera$PreviewCallback",)

#     def __init__(self, callback):
#         super(PreviewCallback, self).__init__()
#         self.callback = callback


# class SurfaceHolderCallback(PythonJavaClass):
#     __javainterfaces__ = ("android.view.SurfaceHolder$Callback",)

#     def __init__(self, callback):
#         super(SurfaceHolderCallback, self).__init__()
#         self.callback = callback

#     @java_method("(Landroid/view/SurfaceHolder;III)V")
#     def surfaceChanged(self, surface, fmt, width, height):
#         self.callback(fmt, width, height)
