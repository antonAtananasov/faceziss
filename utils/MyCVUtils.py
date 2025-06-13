from kivy.graphics.texture import Texture
from enum import Enum
import numpy as np
import cv2


class COLOR_CHANNEL_FORMAT(Enum):
    RGB: str = "rgb"
    RGBA: str = "rgba"
    BGR: str = "bgr"
    BGRA: str = "bgra"
    RGB_AUTO_ALPHA = None
    BGR_AUTO_ALPHA = None


class COLOR_CHANNEL_FORMAT_GROUPS(Enum):
    NON_ALPHA: list[COLOR_CHANNEL_FORMAT] = [
        COLOR_CHANNEL_FORMAT.RGB,
        COLOR_CHANNEL_FORMAT.BGR,
    ]
    WITH_ALPHA: list[COLOR_CHANNEL_FORMAT] = [
        COLOR_CHANNEL_FORMAT.RGBA,
        COLOR_CHANNEL_FORMAT.BGRA,
    ]

    RGB_TYPE: list[COLOR_CHANNEL_FORMAT] = [
        COLOR_CHANNEL_FORMAT.RGB,
        COLOR_CHANNEL_FORMAT.RGBA,
    ]
    BGR_TYPE: list[COLOR_CHANNEL_FORMAT] = [
        COLOR_CHANNEL_FORMAT.BGR,
        COLOR_CHANNEL_FORMAT.BGRA,
    ]

    AUTO_ALPHA = [
        COLOR_CHANNEL_FORMAT.RGB_AUTO_ALPHA,
        COLOR_CHANNEL_FORMAT.BGR_AUTO_ALPHA,
    ]


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

    @staticmethod
    def convertChannelFormat(
        cvImage, inputFormat: COLOR_CHANNEL_FORMAT, outputFormat: COLOR_CHANNEL_FORMAT
    ):
        # does not mutate original image
        image = np.copy(cvImage)

        if inputFormat in COLOR_CHANNEL_FORMAT_GROUPS.AUTO_ALPHA.value:
            imageColorChannelCount = image.shape[2]
            if imageColorChannelCount == 3:
                if inputFormat == COLOR_CHANNEL_FORMAT.RGB_AUTO_ALPHA:
                    inputFormat = COLOR_CHANNEL_FORMAT.RGB
                if inputFormat == COLOR_CHANNEL_FORMAT.BGR_AUTO_ALPHA:
                    inputFormat = COLOR_CHANNEL_FORMAT.BGR
            elif imageColorChannelCount == 4:
                if inputFormat == COLOR_CHANNEL_FORMAT.RGB_AUTO_ALPHA:
                    inputFormat = COLOR_CHANNEL_FORMAT.RGBA
                if inputFormat == COLOR_CHANNEL_FORMAT.BGR_AUTO_ALPHA:
                    inputFormat = COLOR_CHANNEL_FORMAT.BGRA
            else:
                raise Exception("Invalid color channel count for opencv image.")

        if (
            inputFormat in COLOR_CHANNEL_FORMAT_GROUPS.NON_ALPHA.value
            and outputFormat in COLOR_CHANNEL_FORMAT_GROUPS.WITH_ALPHA.value
        ):
            # convert image with no alpha to image with alpha by adding a full alpha channel
            emptyImageChannelMatrix = (
                np.ones((image.shape[0], image.shape[1], 1), np.uint8) * 255
            )
            image = np.append(
                image,
                emptyImageChannelMatrix,
                axis=2,
            )
            pass
        elif (
            inputFormat in COLOR_CHANNEL_FORMAT_GROUPS.WITH_ALPHA.value
            and outputFormat in COLOR_CHANNEL_FORMAT_GROUPS.NON_ALPHA.value
        ):
            image = image[:, :, :-1]
        else:
            pass  # nothing to add/remove

        if (
            inputFormat
            in COLOR_CHANNEL_FORMAT_GROUPS.RGB_TYPE.value
            != outputFormat
            in COLOR_CHANNEL_FORMAT_GROUPS.RGB_TYPE.value
        ):  # swap R and B channels # rgba -> 0,1,2,3
            image = image[
                :,
                :,
                (
                    [2, 1, 0, 3]
                    if outputFormat in (COLOR_CHANNEL_FORMAT_GROUPS.WITH_ALPHA.value)
                    else [2, 1, 0]
                ),
            ]
        else:
            pass  # nothing to swap

        return image

    @staticmethod
    def cvImageToKivyTexture(
        cvImage,
        inputChannelFormat: COLOR_CHANNEL_FORMAT = COLOR_CHANNEL_FORMAT.BGR_AUTO_ALPHA,
        outputChannelFormat: COLOR_CHANNEL_FORMAT = COLOR_CHANNEL_FORMAT.RGBA,
    ) -> Texture:
        # convert it to texture

        if outputChannelFormat != COLOR_CHANNEL_FORMAT.RGBA:
            raise NotImplementedError()

        # keep original image intact
        rgbaImage = MyCVHandler.convertChannelFormat(
            cvImage, inputChannelFormat, outputChannelFormat
        )

        # flip image vertically
        buf1 = cv2.flip(rgbaImage, 0)

        # convert image to bytes
        buf = buf1.tobytes()

        # create texture sized for the image
        cvTexture = Texture.create(
            size=(rgbaImage.shape[1], rgbaImage.shape[0]),
            colorfmt=outputChannelFormat.value,
        )

        # populate texture data from image
        cvTexture.blit_buffer(
            buf, colorfmt=outputChannelFormat.value, bufferfmt="ubyte"
        )

        return cvTexture
