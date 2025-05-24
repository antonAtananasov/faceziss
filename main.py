from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.boxlayout import BoxLayout
from kivy.graphics.texture import Texture
from kivy.clock import Clock
import cv2


class MySettings:
    def __init__(self, fps: float = 60):
        self.fps = fps


class MyCVHandler:
    def __init__(self, cameraIndex: int):
        self.cvCapture = cv2.VideoCapture(cameraIndex)

    def update(self) -> bool:
        # load image from cam
        available, frame = self.cvCapture.read()
        self.available = available

        if self.available:
            self.currentFrame = frame

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
        print("Button Pressed")


class MyApp(App):
    def build(self):
        # app layout
        self.layout = MyBoxLayout()

        # my class objects
        self.settings = MySettings()
        # self.cvMainCamHandler = MyCVHandler(0)
        # self.cvFrontCamHandler = MyCVHandler(1)

        # update loop
        Clock.schedule_interval(self.update, 1 / self.settings.fps)

        return self.layout

    # def update(self, dt):
    #     for cvHandler, cvCanvas in (
    #         (self.cvMainCamHandler, self.layout.cvMainCamCanvas),
    #         (self.cvFrontCamHandler, self.layout.cvFrontCamCanvas),
    #     ):
    #         # update camera
    #         if cvHandler.update():
    #             cvCanvas.texture = cvHandler.cvImageToKivyTexture(
    #                 cvHandler.currentFrame
    #             )
    #         else:
    #             # remove camera canvas if unavailable
    #             self.layout.remove_widget(cvCanvas)


if __name__ == "__main__":
    MyApp().run()
