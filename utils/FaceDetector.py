from utils.CVUtils import (
    HAARCASCADE_ENUM,
    RESOLUTION_ENUM,
    RGB_COLORS_ENUM,
    CVUtils,
)
from cv2.typing import MatLike
from enum import Enum
import numpy as np
import cv2

class EMBEDDING_ALGORITHM_ENUM(Enum):
    pass

class FaceDetector:
    def __init__(
        self,
        haarcascadeClassifier: HAARCASCADE_ENUM,
        maxImageSize: RESOLUTION_ENUM,
    ):
        self.haarcascadeClassifier = cv2.CascadeClassifier(
            cv2.data.haarcascades + haarcascadeClassifier.value
        )
        self.maxImageSize = maxImageSize.value
        self.timingMetrics = {}


    def extractFaceBoundingBoxes(
        self, cvImage: MatLike, resize: bool = True
    ) -> list[tuple[int, int, int, int]]:
        image = CVUtils.optionalResize(cvImage, self.maxImageSize, resize)
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
    def extractForeheadBoundingBox(
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
    def extractCheekBoundingBox(
        rect: tuple[int, int, int, int],
    ) -> tuple[int, int, int, int]:
        x, y, w, h = rect
        return (
            x + w // 6,
            y + int(h * 2.5 // 5),
            w // 6,
            h // 5,
        )


