import cv2.data
from kivy.graphics.texture import Texture
from cv2.typing import MatLike
from enum import Enum
import numpy as np
import cv2


class RESOLUTIONS_ENUM(Enum):
    FHD = (1920, 1080)
    HD = (1280, 720)
    LOW = (640, 480)
    LOWEST = (320, 240)


class FRAMERATES_ENUM(Enum):
    HIGH = 60
    MEDIUM = 30
    LOW = 24
    LOWEST = 15


class HAARCASCADE_FACE_EXTRACTORS_ENUM(Enum):
    FRONTALFACE_ALT = "haarcascade_frontalface_alt.xml"
    FRONTALFACE_DEFAULT = "haarcascade_frontalface_default.xml"


class COLOR_CHANNEL_FORMAT_ENUM(Enum):
    RGB: str = "rgb"
    RGBA: str = "rgba"
    BGR: str = "bgr"
    BGRA: str = "bgra"
    RGB_AUTO_ALPHA = None
    BGR_AUTO_ALPHA = None


class COLOR_CHANNEL_FORMAT_GROUPS_ENUM(Enum):
    NON_ALPHA: list[COLOR_CHANNEL_FORMAT_ENUM] = [
        COLOR_CHANNEL_FORMAT_ENUM.RGB,
        COLOR_CHANNEL_FORMAT_ENUM.BGR,
    ]
    WITH_ALPHA: list[COLOR_CHANNEL_FORMAT_ENUM] = [
        COLOR_CHANNEL_FORMAT_ENUM.RGBA,
        COLOR_CHANNEL_FORMAT_ENUM.BGRA,
    ]

    RGB_TYPE: list[COLOR_CHANNEL_FORMAT_ENUM] = [
        COLOR_CHANNEL_FORMAT_ENUM.RGB,
        COLOR_CHANNEL_FORMAT_ENUM.RGBA,
    ]
    BGR_TYPE: list[COLOR_CHANNEL_FORMAT_ENUM] = [
        COLOR_CHANNEL_FORMAT_ENUM.BGR,
        COLOR_CHANNEL_FORMAT_ENUM.BGRA,
    ]

    AUTO_ALPHA = [
        COLOR_CHANNEL_FORMAT_ENUM.RGB_AUTO_ALPHA,
        COLOR_CHANNEL_FORMAT_ENUM.BGR_AUTO_ALPHA,
    ]


class RGB_COLORS_ENUM(Enum):
    RED = (255, 0, 0)
    GREEN = (0, 255, 0)
    BLUE = (0, 0, 255)
    CYAN = (0, 255, 255)
    MAGENTA = (255, 0, 255)
    YELLOW = (255, 255, 0)
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)


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


class MyFaceDetector:
    def __init__(
        self,
        haarcascadeClassifier: HAARCASCADE_FACE_EXTRACTORS_ENUM,
        maxImageSize: RESOLUTIONS_ENUM,
    ):
        self.haarcascadeClassifier = cv2.CascadeClassifier(
            cv2.data.haarcascades + haarcascadeClassifier.value
        )
        self.maxImageSize = maxImageSize.value
        self.timingMetrics = {}

    def optionalResize(self, cvImage: MatLike, resize: bool = True) -> MatLike:
        return (
            cv2.resize(cvImage, self.maxImageSize)
            if resize
            and cvImage.shape[0] * cvImage.shape[1]
            > self.maxImageSize[0] * self.maxImageSize[1]
            else cvImage
        )

    def extractFaceBoundingBoxes(
        self, cvImage: MatLike, resize: bool = True
    ) -> list[tuple[int, int, int, int]]:
        image = self.optionalResize(cvImage, resize)
        greyscaleImage = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        faceBoundingBoxes = self.haarcascadeClassifier.detectMultiScale(
            greyscaleImage, scaleFactor=1.1, minNeighbors=5, minSize=(40, 40)
        )

        resizedBoundingBoxes = []
        horizontalRatio = cvImage.shape[1] / self.maxImageSize[0]
        verticalRatio = cvImage.shape[0] / self.maxImageSize[1]
        for x, y, w, h in faceBoundingBoxes:
            resizedBoundingBoxes.append(
                (
                    round(x * horizontalRatio),
                    round(y * verticalRatio),
                    round(w * horizontalRatio),
                    round(h * verticalRatio),
                )
            )
        return resizedBoundingBoxes

    @staticmethod
    def faceBoundingToForeheadBounding(
        rect: tuple[int, int, int, int],
    ) -> tuple[int, int, int, int]:
        x, y, w, h = rect
        return (
            x + w * 3 // 8,
            y + h // 12,
            w // 4,
            h // 6,
        )

    @staticmethod
    def faceBoundingToCheekBounding(
        rect: tuple[int, int, int, int],
    ) -> tuple[int, int, int, int]:
        x, y, w, h = rect
        return (
            x + w // 6,
            y + int(h * 2.5 // 5),
            w // 6,
            h // 5,
        )

    @staticmethod
    def putBoundingBoxes(
        cvImage: MatLike,
        rects: list[tuple[int, int, int, int]],
        color: RGB_COLORS_ENUM = RGB_COLORS_ENUM.BLACK,
        thickness: int = 4,
        mutate: bool = False,
    ):
        image = cvImage if mutate else np.copy(cvImage)
        for x, y, w, h in rects:
            cv2.rectangle(
                image,
                (x, y),
                (x + w, y + h),
                color.value,
                thickness,
            )
        return image

    def cropCenter(
        self, cvImage: MatLike, coverage: float, resize: bool = True
    ) -> MatLike:
        # coverage in values between 0 and 1
        newSize = np.array(cvImage.shape) * coverage
        horizontalMargin = int((cvImage.shape[1] - newSize[1]) // 2)
        verticalMargin = int((cvImage.shape[0] - newSize[0]) // 2)

        croppedImage = cvImage[
            verticalMargin : int(cvImage.shape[0] - newSize[0]),
            horizontalMargin : int(cvImage.shape[1] - newSize[1]),
        ]

        return self.optionalResize(croppedImage, resize)
