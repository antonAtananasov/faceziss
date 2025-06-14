from utils.MyCVUtils import COLOR_CHANNEL_FORMAT_ENUM, COLOR_CHANNEL_FORMAT_GROUPS_ENUM
from cv2.typing import MatLike
from collections import deque
import numpy as np
import scipy
import time
import cv2


class MyPulseExtractor:
    def __init__(
        self,
        processingFramerate: float,
        recordingTimeSeconds: float,
        fingerMovementThreshold: float,
        maxImageSize: tuple[int, int],
        maxHeartRate: float,
    ):
        self.expectedFramesCount = processingFramerate * recordingTimeSeconds

        self.sampleBuffer: deque[float] = deque(maxlen=self.expectedFramesCount)
        self.sampleTimeBuffer: deque[float] = deque(maxlen=self.expectedFramesCount)
        self.processingFramerate: float = processingFramerate
        self.recordingTimeSeconds: float = recordingTimeSeconds
        self.fingerMovementThreshold: float = fingerMovementThreshold
        self.pulseSignalAvailable: bool = False
        self.maxImageSize: tuple[int, int] = maxImageSize
        self.averageSamplingRate = float("inf")
        self.window: float = 0
        self.maxHeartRate: float = maxHeartRate

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

    def addFrame(
        self, frame: MatLike, colorFormat: COLOR_CHANNEL_FORMAT_ENUM, resize=True
    ) -> None:
        self.sampleTimeBuffer.append(time.time())

        if colorFormat in COLOR_CHANNEL_FORMAT_GROUPS_ENUM.BGR_TYPE.value:
            channel = 2
        elif colorFormat in COLOR_CHANNEL_FORMAT_GROUPS_ENUM.RGB_TYPE.value:
            channel = 0
        else:
            raise NotImplementedError()

        redHist = MyPulseExtractor.calcHists(frame, colorFormat, [channel])[
            0
        ].reshape((256))
        centerOfMass = np.sum(np.arange(1, len(redHist) + 1) * redHist) / np.sum(
            redHist
        )

        self.sampleBuffer.append(centerOfMass)

        npTimesBuffer = np.array(self.sampleTimeBuffer)
        frametimes = npTimesBuffer[1:] - npTimesBuffer[:-1]
        self.window = npTimesBuffer[-1] - npTimesBuffer[0]
        self.averageSamplingRate = np.average(frametimes)

        self.pulseSignalAvailable = (
            len(self.sampleBuffer) == self.expectedFramesCount
            and abs(self.window - self.recordingTimeSeconds) < 0.05
            and np.std(self.sampleBuffer) < self.fingerMovementThreshold
        )

    def getPulsePeaks(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        signal = np.array(self.sampleBuffer)
        times = np.linspace(0, self.window, len(signal))
        maxHeartRate = self.maxHeartRate
        minRRIntervalDuration = 1 / (maxHeartRate / 60)
        minRRIntervalSamples = minRRIntervalDuration / self.averageSamplingRate
        peakPositions, _ = scipy.signal.find_peaks(
            signal, distance=minRRIntervalSamples
        )
        peakTimes = times[peakPositions]
        peakAmplitudes = signal[peakPositions]

        return peakPositions, peakTimes, peakAmplitudes

    def getBpm(self) -> float:
        _, peakMoments, _ = self.getPulsePeaks()
        RRIntervalDurations = peakMoments[1:] - peakMoments[:-1]
        averageRRIntervalDuration = np.average(RRIntervalDurations)
        bpm = 60 / averageRRIntervalDuration

        return bpm

    def reset(self):
        self.sampleTimeBuffer.clear()
        self.sampleBuffer.clear()
        self.pulseSignalAvailable = False
        self.window = 0
        self.averageSamplingRate = float("inf")

class MyEVMPulseExtractor(MyPulseExtractor):
    def __init__(self, processingFramerate, recordingTimeSeconds, fingerMovementThreshold, maxImageSize, maxHeartRate):
        super().__init__(processingFramerate, recordingTimeSeconds, fingerMovementThreshold, maxImageSize, maxHeartRate)

    def getPulsePeaks(self):
        raise NotImplementedError()
    
    def getBpm(self):
        raise NotImplementedError()