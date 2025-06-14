from utils.MyCVUtils import (
    COLOR_CHANNEL_FORMAT_ENUM,
    COLOR_CHANNEL_FORMAT_GROUPS_ENUM,
    FRAMERATES_ENUM,
    RESOLUTIONS_ENUM,
    RGB_COLORS_ENUM,
)
from kivy.graphics.texture import Texture
from cv2.typing import MatLike
import numpy as np
import cv2


class MyCVHandler:
    NOT_AVAILABLE_IMAGE = None
    NOT_AVAILABLE_TEXTURE = None

    def __init__(
        self,
        cameraIndex: int,
        recordingResolution: RESOLUTIONS_ENUM,
        recordingFramerate: FRAMERATES_ENUM,
    ):
        self.cvCapture = cv2.VideoCapture(cameraIndex)
        self.recordingResolution = recordingResolution.value
        self.recordingFramerate = recordingFramerate.value
        self.cvCapture.set(cv2.CAP_PROP_FRAME_WIDTH, self.recordingResolution[0])
        self.cvCapture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.recordingResolution[1])
        self.cvCapture.set(cv2.CAP_PROP_FPS, self.recordingFramerate)
        self.cvCapture.set(cv2.CAP_PROP_AUTO_WB, 0)
        self.cvCapture.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0)
        self.cvCapture.set(cv2.CAP_PROP_AUTOFOCUS, 1)

        MyCVHandler.NOT_AVAILABLE_IMAGE = np.zeros(
            (self.recordingResolution[1], self.recordingResolution[0], 4), np.uint8
        )
        MyCVHandler.NOT_AVAILABLE_IMAGE[:] = (255, 0, 255, 255)
        cv2.putText(
            MyCVHandler.NOT_AVAILABLE_IMAGE,
            "Not available",
            (0, self.recordingResolution[1] // 2),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
        )
        MyCVHandler.NOT_AVAILABLE_TEXTURE = MyCVHandler.cvImageToKivyTexture(
            MyCVHandler.NOT_AVAILABLE_IMAGE
        )

        self.currentFrame = MyCVHandler.NOT_AVAILABLE_IMAGE

    def getCapProps(self, capProps: list) -> dict:
        result = {}
        for prop in capProps:
            result[prop] = self.cvCapture.get(cv2.CAP_PROP_AUTO_WB)
        return result

    def update(self) -> bool:
        # load image from cam
        available, frame = self.cvCapture.read()
        self.available = available

        self.currentFrame = (
            frame
            if self.available
            and not self.currentFrame is MyCVHandler.NOT_AVAILABLE_IMAGE
            else MyCVHandler.NOT_AVAILABLE_IMAGE
        )

        return self.available

    @staticmethod
    def convertChannelFormat(
        cvImage: MatLike,
        inputFormat: COLOR_CHANNEL_FORMAT_ENUM,
        outputFormat: COLOR_CHANNEL_FORMAT_ENUM,
    ) -> MatLike:
        # does not mutate original image
        image = np.copy(cvImage)

        if inputFormat in COLOR_CHANNEL_FORMAT_GROUPS_ENUM.AUTO_ALPHA.value:
            imageColorChannelCount = image.shape[2]
            if imageColorChannelCount == 3:
                if inputFormat == COLOR_CHANNEL_FORMAT_ENUM.RGB_AUTO_ALPHA:
                    inputFormat = COLOR_CHANNEL_FORMAT_ENUM.RGB
                if inputFormat == COLOR_CHANNEL_FORMAT_ENUM.BGR_AUTO_ALPHA:
                    inputFormat = COLOR_CHANNEL_FORMAT_ENUM.BGR
            elif imageColorChannelCount == 4:
                if inputFormat == COLOR_CHANNEL_FORMAT_ENUM.RGB_AUTO_ALPHA:
                    inputFormat = COLOR_CHANNEL_FORMAT_ENUM.RGBA
                if inputFormat == COLOR_CHANNEL_FORMAT_ENUM.BGR_AUTO_ALPHA:
                    inputFormat = COLOR_CHANNEL_FORMAT_ENUM.BGRA
            else:
                raise Exception("Invalid color channel count for opencv image.")

        if (
            inputFormat in COLOR_CHANNEL_FORMAT_GROUPS_ENUM.NON_ALPHA.value
            and outputFormat in COLOR_CHANNEL_FORMAT_GROUPS_ENUM.WITH_ALPHA.value
        ):
            # convert image with no alpha to image with alpha by adding a full alpha channel
            emptyImageChannelMatrix = np.full(
                (image.shape[0], image.shape[1], 1), 255, np.uint8
            )
            image = np.append(
                image,
                emptyImageChannelMatrix,
                axis=2,
            )
            pass
        elif (
            inputFormat in COLOR_CHANNEL_FORMAT_GROUPS_ENUM.WITH_ALPHA.value
            and outputFormat in COLOR_CHANNEL_FORMAT_GROUPS_ENUM.NON_ALPHA.value
        ):
            image = image[:, :, :-1]
        else:
            pass  # nothing to add/remove

        if (
            inputFormat
            in COLOR_CHANNEL_FORMAT_GROUPS_ENUM.RGB_TYPE.value
            != outputFormat
            in COLOR_CHANNEL_FORMAT_GROUPS_ENUM.RGB_TYPE.value
        ):  # swap R and B channels # rgba -> 0,1,2,3
            image = image[
                :,
                :,
                (
                    [2, 1, 0, 3]
                    if outputFormat
                    in (COLOR_CHANNEL_FORMAT_GROUPS_ENUM.WITH_ALPHA.value)
                    else [2, 1, 0]
                ),
            ]
        else:
            pass  # nothing to swap

        return image

    @staticmethod
    def cvImageToKivyTexture(
        cvImage: MatLike,
        inputChannelFormat: COLOR_CHANNEL_FORMAT_ENUM = COLOR_CHANNEL_FORMAT_ENUM.BGR_AUTO_ALPHA,
        outputChannelFormat: COLOR_CHANNEL_FORMAT_ENUM = COLOR_CHANNEL_FORMAT_ENUM.RGBA,
    ) -> Texture:
        # convert it to texture

        if outputChannelFormat != COLOR_CHANNEL_FORMAT_ENUM.RGBA:
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

    def increaseExposure(self):
        currentExposure = self.cvCapture.get(cv2.CAP_PROP_GAIN)
        self.cvCapture.set(cv2.CAP_PROP_GAIN, currentExposure + 1)
        newExposure = currentExposure = self.cvCapture.get(cv2.CAP_PROP_GAIN)
        print("Changing exposure to", newExposure)

    def decreaseExposure(self):
        currentExposure = self.cvCapture.get(cv2.CAP_PROP_GAIN)
        self.cvCapture.set(cv2.CAP_PROP_GAIN, currentExposure - 1)
        newExposure = currentExposure = self.cvCapture.get(cv2.CAP_PROP_GAIN)
        print("Changing exposure to", newExposure)

    @staticmethod
    def plotData(
        cvImage: MatLike,
        data: list[float],
        color: RGB_COLORS_ENUM,
        thickness: int = 1,
        mutate: bool = False,
        plotCenterOfMass=True,
        maxValue: float = None,
        minValue: float = None,
    ):
        image = cvImage if mutate else np.copy(cvImage)
        if not len(data):
            return image

        maxValue = maxValue or np.max(data)
        minValue = minValue or np.min(data)
        imageHeight, imageWidth = image.shape[0], image.shape[1]

        y = np.interp(np.array(data), [minValue, maxValue], [0, imageHeight])
        x = np.linspace(0, imageWidth, len(data))

        displayPts = np.array(np.column_stack((x, imageHeight - y)), np.int32)
        displayPts = displayPts.reshape((-1, 1, 2))

        cv2.polylines(image, [displayPts], False, color.value, thickness)

        if plotCenterOfMass:
            centerOfMass = round(np.sum(x * y) / np.sum(y))
            cv2.line(
                image,
                (int(centerOfMass), 0),
                (int(centerOfMass), imageHeight - 1),
                color.value,
                thickness,
            )
            pass

        return image
