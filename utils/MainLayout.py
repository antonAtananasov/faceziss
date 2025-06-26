from utils.LayoutUtils import HorizontalElementLayout
from utils.SettingsManager import SettingsManager
from kivy.properties import ListProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.image import Image


class MainLayout(BoxLayout):
    camera_size = ListProperty(list(SettingsManager.RECODRING_IMAGE_SIZE.value))

    def __init__(self, actions: dict[str, callable], **kwargs):
        super(MainLayout, self).__init__(**kwargs)
        self.orientation = "vertical"

        self.cvMainCamCanvas: Image = Image()
        self.add_widget(self.cvMainCamCanvas)

        self.cvFrontCamCanvas: Image = Image()
        self.add_widget(self.cvFrontCamCanvas)

        self.actionButtons: list[Button] = []
        for actionName, actionDelegate in actions.items():
            button = Button(text=actionName, font_size=32)
            button.bind(on_press=actionDelegate)
            self.actionButtons.append(button)

        self.add_widget(HorizontalElementLayout(self.actionButtons))
