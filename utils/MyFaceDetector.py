from utils.MyCVUtils import (
    HAARCASCADE_FACE_EXTRACTORS_ENUM,
    RESOLUTIONS_ENUM,
    RGB_COLORS_ENUM,
    MyCVUtils,
)
from cv2.typing import MatLike
import numpy as np
import cv2


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
        return MyCVUtils.optionalResize(cvImage, self.maxImageSize, resize)

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
