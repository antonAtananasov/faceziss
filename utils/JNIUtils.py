from jnius import autoclass, PythonJavaClass, java_method
import kivy
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
