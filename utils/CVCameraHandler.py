from utils.CVUtils import (
    FRAMERATE_ENUM,
    RESOLUTION_ENUM,
    CVUtils
)
import numpy as np
import cv2


class CVCameraHandler:
    NOT_AVAILABLE_IMAGE = None
    NOT_AVAILABLE_TEXTURE = None

    def __init__(
        self,
        cameraIndex: int,
        recordingResolution: RESOLUTION_ENUM,
        recordingFramerate: FRAMERATE_ENUM,
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

        CVCameraHandler.NOT_AVAILABLE_IMAGE = np.zeros(
            (self.recordingResolution[1], self.recordingResolution[0], 4), np.uint8
        )
        CVCameraHandler.NOT_AVAILABLE_IMAGE[:] = (255, 0, 255, 255)
        cv2.putText(
            CVCameraHandler.NOT_AVAILABLE_IMAGE,
            "Not available",
            (0, self.recordingResolution[1] // 2),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
        )
        CVCameraHandler.NOT_AVAILABLE_TEXTURE = CVUtils.cvImageToKivyTexture(
            CVCameraHandler.NOT_AVAILABLE_IMAGE
        )

        self.currentFrame = CVCameraHandler.NOT_AVAILABLE_IMAGE

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
            and not self.currentFrame is CVCameraHandler.NOT_AVAILABLE_IMAGE
            else CVCameraHandler.NOT_AVAILABLE_IMAGE
        )

        return self.available


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

