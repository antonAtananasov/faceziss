from kivy.graphics.texture import Texture
from abc import ABC as AbstractClass
from enum import Enum
import numpy as np
import cv2

MatLike = np.ndarray

class RESOLUTION_ENUM(Enum):
    FHD = (1920, 1080)
    HD = (1280, 720)
    LOW = (640, 480)
    LOWEST = (320, 240)


class FRAMERATE_ENUM(Enum):
    HIGH = 60
    MEDIUM = 30
    LOW = 20
    LOWEST = 15


class HAARCASCADE_ENUM(Enum):
    FRONTALFACE_ALT = "assets/classifiers/haarcascade_frontalface_alt.xml"
    FRONTALFACE_DEFAULT = "assets/classifiers/haarcascade_frontalface_default.xml"


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
        COLOR_CHANNEL_FORMAT_ENUM.RGB_AUTO_ALPHA,
    ]
    BGR_TYPE: list[COLOR_CHANNEL_FORMAT_ENUM] = [
        COLOR_CHANNEL_FORMAT_ENUM.BGR,
        COLOR_CHANNEL_FORMAT_ENUM.BGRA,
        COLOR_CHANNEL_FORMAT_ENUM.BGR_AUTO_ALPHA,
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
    GREY = (128, 128, 128)


class ICON_ENUM(AbstractClass):
    # PNGs of size 512x512
    NO_TOUCH = cv2.imread("assets/images/no-touch.png", cv2.IMREAD_UNCHANGED)
    TOUCH = cv2.imread("assets/images/touch.png", cv2.IMREAD_UNCHANGED)
    FACE = cv2.imread("assets/images/face.png", cv2.IMREAD_UNCHANGED)


class CVUtils:
    @staticmethod
    def optionalResize(
        cvImage: MatLike, resolution: tuple[int, int], resize: bool = True
    ) -> MatLike:
        # TODO: check if image is under required size
        return (
            cv2.resize(cvImage, resolution)
            if resize
            and cvImage.shape[0] * cvImage.shape[1] > resolution[0] * resolution[1]
            else cvImage
        )

    @staticmethod
    def cropToRect(image: MatLike, rect: tuple[int, int, int, int]) -> MatLike:
        x, y, w, h = rect
        return image[x : x + w, y : y + h]

    @staticmethod
    def calcHists(
        image: MatLike,
        colorFormat: COLOR_CHANNEL_FORMAT_ENUM,
        channels: list[int] = None,
    ) -> list[np.ndarray]:
        if channels == None:
            if colorFormat in COLOR_CHANNEL_FORMAT_GROUPS_ENUM.BGR_TYPE.value:
                channels = [2, 1, 0]
            elif colorFormat in COLOR_CHANNEL_FORMAT_GROUPS_ENUM.RGB_TYPE.value:
                channels = [0, 1, 2]
            else:
                raise NotImplementedError()

        hists = [
            cv2.calcHist([image], [channel], None, [256], [0, 256]).reshape(256)
            for channel in channels
        ]
        return hists

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
        rgbaImage = CVUtils.convertChannelFormat(
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

    @staticmethod
    def putBoundingBoxes(
        cvImage: MatLike,
        rects: list[tuple[int, int, int, int]],
        color: RGB_COLORS_ENUM = RGB_COLORS_ENUM.BLACK,
        thickness: int = 1,
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

    @staticmethod
    def cropCenter(cvImage: MatLike, coverage: float, resize: bool = True) -> MatLike:
        # coverage in values between 0 and 1
        newSize = np.array(cvImage.shape) * coverage
        horizontalMargin = int((cvImage.shape[1] - newSize[1]) // 2)
        verticalMargin = int((cvImage.shape[0] - newSize[0]) // 2)

        croppedImage = cvImage[
            verticalMargin : int(cvImage.shape[0] - newSize[0]),
            horizontalMargin : int(cvImage.shape[1] - newSize[1]),
        ]

        return croppedImage

    @staticmethod
    def overlayIcon(bg: MatLike, icon: MatLike, position: tuple[int, int]) -> MatLike:
        x, y = position
        if icon.shape[2] != 4:
            raise ValueError("Icon must have 4 channels (BGRA)")

        h, w = icon.shape[:2]
        bg_h, bg_w = bg.shape[:2]

        # Clip region if it exceeds background bounds
        if x + w > bg_w or y + h > bg_h:
            w = min(w, bg_w - x)
            h = min(h, bg_h - y)
            icon = icon[0:h, 0:w]

        # Extract the alpha mask and normalize
        alpha = icon[:, :, 3:4] / 255.0
        icon_bgr = icon[:, :, :3]

        # Perform blending
        bg_roi = bg[y : y + h, x : x + w, :3]
        blended = (1.0 - alpha) * bg_roi + alpha * icon_bgr
        bg[y : y + h, x : x + w, :3] = blended.astype(bg.dtype)

        return bg

    @staticmethod
    def recolor(
        image: MatLike, format: COLOR_CHANNEL_FORMAT_ENUM, color: RGB_COLORS_ENUM
    ) -> MatLike:
        r, g, b = color.value[:3]
        if format in COLOR_CHANNEL_FORMAT_GROUPS_ENUM.BGR_TYPE.value:
            r, b = b, r

        factor = (r, g, b)
        if format in COLOR_CHANNEL_FORMAT_GROUPS_ENUM.WITH_ALPHA.value:
            factor = (r, g, b, 255)

        return image * (np.array(factor) / 255)

    @staticmethod
    def putIcon(
        image: MatLike,
        icon: ICON_ENUM,
        position: tuple[int, int],
        size: tuple[int, int],
        color: RGB_COLORS_ENUM,
        format: COLOR_CHANNEL_FORMAT_ENUM,
    ) -> None:
        icon = icon
        icon = CVUtils.optionalResize(icon, size, True)
        icon = CVUtils.recolor(icon, format, color)
        CVUtils.overlayIcon(image, icon, position)

    @staticmethod
    def calcSharpness(image: MatLike) -> float:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        lap = cv2.Laplacian(image, cv2.CV_16S)
        mean, stddev = cv2.meanStdDev(lap)
        return stddev[0, 0]

    @staticmethod
    def putProgressRect(
        img: MatLike,
        rect: tuple[int, int, int, int],
        progress: float,
        color: RGB_COLORS_ENUM,
        thickness: int = 2,
    ):
        x, y, w, h = rect
        p = max(0.0, min(1.0, float(progress)))  # Clamp to [0.0, 1.0]

        # Define key points
        points = [
            (x + w // 2, y),        # 0 - top center
            (x + w, y),             # 1 - top right
            (x + w, y + h),         # 2 - bottom right
            (x, y + h),             # 3 - bottom left
            (x, y),                 # 4 - top left
            (x + w // 2, y)         # 5 - back to top center
        ]

        # Segment lengths (may contain 0 if w or h = 0)
        seg_lengths = [
            w / 2, h, w, h, w / 2
        ]
        total_length = sum(seg_lengths)
        
        if total_length == 0:
            return  # Nothing to draw

        draw_length = p * total_length

        for i in range(len(seg_lengths)):
            seg_len = seg_lengths[i]
            pt1 = points[i]
            pt2 = points[i + 1]

            if seg_len <= 0:
                continue  # Avoid division by zero

            if draw_length <= 0:
                break

            if draw_length >= seg_len:
                cv2.line(img, pt1, pt2, color.value, thickness)
                draw_length -= seg_len
            else:
                # Partial draw
                dx = pt2[0] - pt1[0]
                dy = pt2[1] - pt1[1]
                ratio = draw_length / seg_len
                px = int(round(pt1[0] + dx * ratio))
                py = int(round(pt1[1] + dy * ratio))
                cv2.line(img, pt1, (px, py), color.value, thickness)
                break