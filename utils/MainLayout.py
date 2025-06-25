from utils.LayoutUtils import HorizontalElementLayout
from utils.SettingsManager import SettingsManager
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.app import App
import numpy as np
import kivy
from kivy.properties import (
    ListProperty,
)

if kivy.platform == "android":
    from utils.JNIManager import (
        FrameCallback,
        JniusPythonActivityContext,
        LogicalCameraToRGB,
        TonzissCameraChecker,
    )


class MainLayout(BoxLayout):
    camera_size = ListProperty(list(SettingsManager.RECODRING_IMAGE_SIZE.value))

    def __init__(self, **kwargs):
        super(MainLayout, self).__init__(**kwargs)
        self.orientation = "vertical"

        self.cvMainCamCanvas = Image()
        self.add_widget(self.cvMainCamCanvas)

        self.cvFrontCamCanvas = Image()
        self.add_widget(self.cvFrontCamCanvas)

        # create widget
        button1 = Button(text="Click Me!")
        mainApp: App = App.get_running_app()
        button1.bind(
            on_press=lambda instance: print(
                np.array(mainApp.fingerPulseExtractor.sampleBuffer),
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

        self.add_widget(HorizontalElementLayout([button1, button2, button3]))

    def on_button_press(self, instance):
        # app = App.get_running_app()
        tonzissCameraChecker = TonzissCameraChecker(JniusPythonActivityContext)
        logicalCameraToRGB = LogicalCameraToRGB(
            JniusPythonActivityContext,
            SettingsManager.RECODRING_IMAGE_SIZE.value[0],
            SettingsManager.RECODRING_IMAGE_SIZE.value[1],
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
