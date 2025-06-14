import cv2.data
from cv2.typing import MatLike
from enum import Enum
import numpy as np
import cv2
from collections import deque
import scipy
import time


class RESOLUTIONS_ENUM(Enum):
    FHD = (1920, 1080)
    HD = (1280, 720)
    LOW = (640, 480)
    LOWEST = (320, 240)


class FRAMERATES_ENUM(Enum):
    HIGH = 60
    MEDIUM = 30
    LOW = 20
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


class MyCVUtils:
    @staticmethod
    def optionalResize(
        cvImage: MatLike, resolution: tuple[int, int], resize: bool = True
    ) -> MatLike:
        return (
            cv2.resize(cvImage, resolution)
            if resize
            and cvImage.shape[0] * cvImage.shape[1] > resolution[0] * resolution[1]
            else cvImage
        )
    
    @staticmethod
    def cropToRect(image:MatLike, rect:tuple[int,int,int,int])->MatLike:
        x,y,w,h=rect
        return image[x:x+w,y:y+h]



