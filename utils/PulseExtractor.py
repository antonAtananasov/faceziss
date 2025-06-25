import scipy.signal
from utils.CVUtils import (
    COLOR_CHANNEL_FORMAT_ENUM,
    RGB_COLORS_ENUM,
)
from abc import ABC as AbstractClass
from utils.CVUtils import CVUtils
from cv2.typing import MatLike
from collections import deque
import numpy as np
import scipy
import time
import cv2


class PulseExtractor(AbstractClass):
    def __init__(
        self,
        processingFramerate: float,
        targetRecordingWindow: float,
        targetClarityThreshold: float,
        maxImageSize: tuple[int, int],
        frequencyRangeBPM: tuple[float, float],
        bandpassOrder:int
    ):
        self.expectedFramesCount: int = int(processingFramerate * targetRecordingWindow)

        self.sampleBuffer: deque[float] = deque(maxlen=self.expectedFramesCount)
        self.sampleTimeBuffer: deque[float] = deque(maxlen=self.expectedFramesCount)
        self.processingFramerate: float = processingFramerate
        self.targetRecordingWindow: float = targetRecordingWindow
        self.targetClarityThreshold: float = targetClarityThreshold
        self.pulseSignalAvailable: bool = False
        self.maxImageSize: tuple[int, int] = maxImageSize
        self.averageSamplingRate = float("inf")
        self.targetMovement = float("inf")
        self.totalRecordingTime: float = 0
        self.minHeartRate: float = frequencyRangeBPM[0]
        self.maxHeartRate: float = frequencyRangeBPM[1]
        self.bandpassOrder:int=bandpassOrder

    def addFrame(self, frame: MatLike, colorFormat: COLOR_CHANNEL_FORMAT_ENUM) -> None:
        self.sampleTimeBuffer.append(time.time())

        channel = 1  # green
        hist = CVUtils.calcHists(frame, colorFormat, [channel])[0].reshape((256))
        centerOfMass = np.sum(np.arange(1, len(hist) + 1) * hist) / np.sum(hist)

        self.sampleBuffer.append(centerOfMass)

        npTimesBuffer = np.array(self.sampleTimeBuffer)
        frametimes = npTimesBuffer[1:] - npTimesBuffer[:-1]
        self.averageSamplingRate = np.average(frametimes)
        self.totalRecordingTime = (
            npTimesBuffer[-1] - npTimesBuffer[0] + self.averageSamplingRate
        )

    def getPulsePeaks(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        raise NotImplementedError()

    def getBPM(self) -> float:
        raise NotImplementedError()

    def plotPulseWave(self, image, color: RGB_COLORS_ENUM):
        signal = self.bandpass(self.sampleBuffer)

        window = self.totalRecordingTime
        _, t, a = self.getPulsePeaks()
        CVUtils.plotData(
            image,
            signal,
            color,
            plotCenterOfMass=False,
            mutate=True,
        )
        for i in range(len(t)):
            x = t[i] / window * image.shape[1]
            y = image.shape[0] - np.interp(
                a[i],
                [np.min(signal), np.max(signal)],
                [0, image.shape[0]],
            )
            p = np.int32((x, y))
            cv2.circle(image, p, 5, color.value, cv2.FILLED)

    def bandpass(self, signal):
        n=self.bandpassOrder
        b=[1/n]*n
        a=1
        bandpassedSignal = scipy.signal.lfilter(b,a,signal)[n:]
        return bandpassedSignal

    def reset(self):
        self.sampleTimeBuffer.clear()
        self.sampleBuffer.clear()
        self.pulseSignalAvailable = False
        self.totalRecordingTime = 0
        self.averageSamplingRate = float("inf")
        self.targetMovement = float("inf")


class PPGPulseExtractor(PulseExtractor):
    def __init__(
        self,
        processingFramerate,
        recordingTimeSeconds,
        fingerMovementThreshold,
        maxImageSize,
        frequencyRangeBPM,
        bandpassOrder
    ):
        super().__init__(
            processingFramerate,
            recordingTimeSeconds,
            fingerMovementThreshold,
            maxImageSize,
            frequencyRangeBPM,
            bandpassOrder
        )
        self.hasFinger = False
        self.hasFingerFlagBuffer: deque[bool] = deque(maxlen=self.expectedFramesCount)

    def detectFinger(self, image: MatLike) -> bool:
        self.hasFinger = CVUtils.calcSharpness(image) < self.targetClarityThreshold
        return self.hasFinger

    def addFrame(self, frame, colorFormat):
        super().addFrame(frame, colorFormat)
        self.hasFingerFlagBuffer.append(self.detectFinger(frame))
        if not self.hasFinger:
            self.reset()
        self.targetMovement = np.std(self.sampleBuffer)
        self.pulseSignalAvailable = not self.requiresRecording() and all(
            self.hasFingerFlagBuffer
        )

    def requiresRecording(self):
        return (
            len(self.sampleBuffer) < self.expectedFramesCount
            or self.totalRecordingTime < self.targetRecordingWindow
        )

    def getPulsePeaks(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        signal = self.bandpass(self.sampleBuffer)

        times = np.linspace(0, self.totalRecordingTime, len(signal))
        maxHeartRate = self.maxHeartRate
        minRRIntervalDuration = 60 / maxHeartRate
        minRRIntervalSamples = minRRIntervalDuration / self.averageSamplingRate
        peakPositions, _ = scipy.signal.find_peaks(
            signal, distance=minRRIntervalSamples
        )
        peakTimes = times[peakPositions]
        peakAmplitudes = signal[peakPositions]

        return peakPositions, peakTimes, peakAmplitudes

    def getBPM(self) -> float:
        _, peakMoments, _ = self.getPulsePeaks()
        RRIntervalDurations = peakMoments[1:] - peakMoments[:-1]
        averageRRIntervalDuration = np.average(RRIntervalDurations)
        bpm = 60 / averageRRIntervalDuration

        return bpm

    def reset(self):
        super().reset()
        self.hasFingerFlagBuffer.clear()
        self.hasFinger = False


class EVMPulseExtractor(PulseExtractor):
    def __init__(
        self,
        processingFramerate,
        recordingTimeSeconds,
        fingerMovementThreshold,
        maxImageSize,
        frequencyRangeBPM,
    ):
        super().__init__(
            processingFramerate,
            recordingTimeSeconds,
            fingerMovementThreshold,
            maxImageSize,
            frequencyRangeBPM,
        )

    def getPulsePeaks(self):
        raise NotImplementedError()

    def getBPM(self):
        raise NotImplementedError()
