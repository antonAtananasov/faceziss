import kivy
from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.boxlayout import BoxLayout
from kivy.graphics.texture import Texture
from kivy.clock import Clock
import cv2
import numpy as np

PERMISSIONS_LIST = []
if kivy.platform == "android":
    from android.permissions import (  # pylint: disable=import-error # type: ignore
            request_permissions,
            Permission,
            check_permission,
        )
    PERMISSIONS_LIST = [Permission.CAMERA]

def requestPermissions(permissionsList:list=PERMISSIONS_LIST):
    print("Requesting permissions:", permissionsList)
    if kivy.platform == "android":
        request_permissions(permissionsList)

def checkPermissions(permissionsList:list=PERMISSIONS_LIST):
    hasPermissions=[]
    if kivy.platform == "android":
        hasPermissions=[check_permission(p) for p in permissionsList]
        if not all(hasPermissions):
            print("Requesting one or more permissions failed")
    return hasPermissions


class MySettings:
    def __init__(self, fps: float = 60):
        self.fps = fps


class MyCVHandler:
    def __init__(self, cameraIndex: int):
        self.cvCapture = cv2.VideoCapture(cameraIndex)

        self.notAvailableImage = np.ones((240, 320, 3)) * 128
        cv2.putText(
            self.notAvailableImage,
            "Not available",
            (0, 120),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (255, 255, 255),
        )

    def update(self) -> bool:
        # load image from cam
        available, frame = self.cvCapture.read()
        self.available = available

        self.currentFrame = frame if self.available else self.notAvailableImage

        return self.available

    def cvImageToKivyTexture(self, cvImage) -> Texture:
        # convert it to texture
        buf1 = cv2.flip(cvImage, 0)
        buf = buf1.tobytes()
        cvTexture = Texture.create(
            size=(cvImage.shape[1], cvImage.shape[0]), colorfmt="bgr"
        )
        # if working on RASPBERRY PI, use colorfmt='rgba' here instead, but stick with "bgr" in blit_buffer.
        cvTexture.blit_buffer(buf, colorfmt="bgr", bufferfmt="ubyte")

        return cvTexture


class MyBoxLayout(BoxLayout):
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
        print(PERMISSIONS_LIST,checkPermissions(PERMISSIONS_LIST))


class MyApp(App):
    def build(self):
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


if __name__ == "__main__":
    requestPermissions()
    MyApp().run()
