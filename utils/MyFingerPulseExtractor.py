from MyCVUtils import (
    COLOR_FMT,COLOR_CHANNEL_FORMAT_GROUPS_ENUM
)
from cv2.typing import MatLike
from collections import deque
import numpy as np
import scipy
import time
import cv2

class MyFingerPulseExtractor:
    def __init__(
        self,
        processingFramerate: float,
        recordingTimeSeconds: float,
        fingerMovementThreshold: float,
        maxImageSize: tuple[int, int],
        maxHeartRate: float,
    ):
        self.expectedFramesCount = processingFramerate * recordingTimeSeconds

        self.centerOfMassesBuffer = deque(maxlen=self.expectedFramesCount)
        self.timesBuffer = deque(maxlen=self.expectedFramesCount)
        self.processingFramerate = processingFramerate
        self.recordingTimeSeconds = recordingTimeSeconds
        self.fingerMovementThreshold = fingerMovementThreshold
        self.pulseSignalAvailable = False
        self.pulseFft = None
        self.maxImageSize = maxImageSize
        self.averageSamplingRate: float = None
        self.window: float = None
        self.maxHeartRate = maxHeartRate

    @staticmethod
    def calcHists(
        image: MatLike,
        colorFormat: COLOR_FMT,
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
        self, frame: MatLike, colorFormat: COLOR_FMT, resize=True
    ) -> None:
        self.timesBuffer.append(time.time())

        if colorFormat in COLOR_CHANNEL_FORMAT_GROUPS_ENUM.BGR_TYPE.value:
            channel = 2
        elif colorFormat in COLOR_CHANNEL_FORMAT_GROUPS_ENUM.RGB_TYPE.value:
            channel = 0
        else:
            raise NotImplementedError()

        redHist = MyFingerPulseExtractor.calcHists(frame, colorFormat, [channel])[
            0
        ].reshape((256))
        centerOfMass = np.sum(np.arange(1, len(redHist) + 1) * redHist) / np.sum(
            redHist
        )

        self.centerOfMassesBuffer.append(centerOfMass)

        npTimesBuffer = np.array(self.timesBuffer)
        frametimes = npTimesBuffer[1:] - npTimesBuffer[:-1]
        self.window = npTimesBuffer[-1] - npTimesBuffer[0]
        self.averageSamplingRate = np.average(frametimes)

        self.pulseSignalAvailable = (
            self.window >= self.recordingTimeSeconds
            and np.std(self.centerOfMassesBuffer) < self.fingerMovementThreshold
        )

        # if self.pulseSignalAvailable:
        # scaleFactor = 4
        # signal = np.resize(
        #     self.centerOfMassesBuffer, len(self.centerOfMassesBuffer) * scaleFactor
        # )

        # y = np.fft.fft(signal)
        # mag = np.abs(y)
        # fmax = 1 / averageFrameTime
        # fstep = fmax / (len(self.centerOfMassesBuffer) - 1)

        # freq = np.arange(0, fmax + fstep, fstep/scaleFactor)
        # print(freq, mag / (len(self.centerOfMassesBuffer) / 2))

    def getPulsePeaks(self) -> tuple[np.ndarray,np.ndarray,np.ndarray]:
        signal = np.array(self.centerOfMassesBuffer)
        times = np.linspace(0, self.window, len(signal))
        maxHeartRate = self.maxHeartRate
        minRRIntervalDuration = 1 / (maxHeartRate / 60)
        minRRIntervalSamples = minRRIntervalDuration / self.averageSamplingRate
        peakPositions, _ = scipy.signal.find_peaks(signal, distance=minRRIntervalSamples)
        peakTimes = times[peakPositions]
        peakAmplitudes = signal[peakPositions]

        return peakPositions, peakTimes, peakAmplitudes

    def getBpm(self) -> float:
        peaks, peakMoments, peakAmplitudes = self.getPulsePeaks()
        RRIntervalDurations = peakMoments[1:] - peakMoments[:-1]
        averageRRIntervalDuration = np.average(RRIntervalDurations)
        bpm = 60 / averageRRIntervalDuration

        return bpm