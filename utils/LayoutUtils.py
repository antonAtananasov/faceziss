from kivy.uix.boxlayout import BoxLayout

class HorizontalElementLayout(BoxLayout):
    def __init__(self, elements: list, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "horizontal"
        for element in elements:
            self.add_widget(element)
