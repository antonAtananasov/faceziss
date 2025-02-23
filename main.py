from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout


class MyLayout(BoxLayout):
    def __init__(self, **kwargs):
        super(MyLayout, self).__init__(**kwargs)
        self.orientation = "vertical"

        label1 = Label(text="Hello World!")

        self.add_widget(label1)

        button1 = Button(text="Click Me!")
        button1.bind(on_press=self.on_button_press)

        self.add_widget(button1)

    def on_button_press(self, instance):
        print("Button Pressed")


class MyApp(App):
    def build(self):
        return MyLayout()


if __name__ == "__main__":
    MyApp().run()
