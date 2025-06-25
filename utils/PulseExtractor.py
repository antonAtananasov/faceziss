from utils.CVUtils import (
    COLOR_CHANNEL_FORMAT_ENUM,
    RGB_COLORS_ENUM,
)
from utils.CVUtils import CVUtils, MatLike
from abc import ABC as AbstractClass
from collections import deque
import numpy as np
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
        bandpassOrder: int,
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
        self.averageSamplingFreq: float = 0
        self.targetMovement = float("inf")
        self.totalRecordingTime: float = 0
        self.minHeartRate: float = frequencyRangeBPM[0]
        self.maxHeartRate: float = frequencyRangeBPM[1]
        self.bandpassOrder: int = bandpassOrder

        self.minSampleFreq = self.minHeartRate / 60
        self.maxSampleFreq = self.maxHeartRate / 60
        self.minRRIntervalDuration = 60 / self.maxHeartRate
        self.minRRIntervalSamples = (
            self.minRRIntervalDuration / self.processingFramerate
        )

    def findPeaks(
        self, signal: np.ndarray, threshold: float = 0.5, min_distance: int = 1
    ):
        """
        Find peaks in 1D noisy data without using SciPy.

        Parameters:
        - y: 1D numpy array of data
        - threshold: minimum height a peak must have (relative to max(y))
        - min_distance: minimum number of samples between adjacent peaks

        Returns:
        - peaks_indices: indices of detected peaks
        """
        peaks = []
        signal = np.asarray(signal)
        threshold_abs = np.interp(threshold, [0, 1], [np.min(signal), np.max(signal)])

        for i in range(1, len(signal) - 1):
            # Local max only
            if signal[i - 1] < signal[i] > signal[i + 1] and signal[i] >= threshold_abs:
                if peaks and i - peaks[-1] < min_distance:
                    if signal[i] > signal[peaks[-1]]:
                        peaks[-1] = i  # Replace with the higher peak
                else:
                    peaks.append(i)

        return np.array(peaks)

    def addFrame(self, frame: MatLike, colorFormat: COLOR_CHANNEL_FORMAT_ENUM) -> None:
        self.sampleTimeBuffer.append(time.time())

        channel = 1  # green
        hist = CVUtils.calcHists(frame, colorFormat, [channel])[0].reshape((256))
        centerOfMass = np.sum(np.arange(1, len(hist) + 1) * hist) / np.sum(hist)

        self.sampleBuffer.append(centerOfMass)
        self.minRRIntervalSamples = (
            self.minRRIntervalDuration / self.averageSamplingRate
        )

        npTimesBuffer = np.array(self.sampleTimeBuffer)
        frametimes = npTimesBuffer[1:] - npTimesBuffer[:-1]
        self.averageSamplingRate = np.average(frametimes)
        self.averageSamplingFreq = 1 / self.averageSamplingRate
        self.totalRecordingTime = (
            npTimesBuffer[-1] - npTimesBuffer[0] + self.averageSamplingRate
        )

    def getPulsePeaks(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        raise NotImplementedError()

    def getBPM(self) -> float:
        raise NotImplementedError()

    def getSignal(self, bandpass: bool = False) -> np.ndarray:
        signal = np.interp(
            self.sampleBuffer,
            [np.min(self.sampleBuffer), np.max(self.sampleBuffer)],
            [-1, 1],
        )
        if bandpass:
            signal = self.bandpass(
                self.sampleBuffer,
                self.averageSamplingFreq,
                self.minSampleFreq,
                self.maxSampleFreq,
            )
        signal = signal[
            np.where(
                np.array(self.sampleTimeBuffer) - self.sampleTimeBuffer[-1]
                <= self.targetRecordingWindow
            )
        ]
        return signal

    def getFFT(self, signal) -> tuple[np.ndarray, np.ndarray]:
        N = len(signal)
        zero_padding_factor = 10
        padded_length = N * zero_padding_factor
        window = np.hanning(N)
        y = np.array(signal) * window
        X = np.fft.fft(y, n=padded_length)
        freq = np.linspace(0, 1 / self.averageSamplingRate * 60, padded_length)
        mask = np.where((freq >= self.minHeartRate) & (freq <= self.maxHeartRate))
        return freq[mask], np.abs(X.real)[mask]

    def getPeakFreq(self, signal) -> float:
        freqs, amps = self.getFFT(signal)
        peakIdx = np.where(amps == np.max(amps))
        return round(freqs[peakIdx][0])

    def plotPulseWave(self, image, color: RGB_COLORS_ENUM):
        signal = self.getSignal()
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

    def bandpass(self, signal, fs, f_low, f_high):
        """
        Bandpass filter using FFT (pure NumPy).

        Parameters:
        - signal: 1D NumPy array (time domain)
        - fs: Sampling frequency (Hz)
        - f_low: Lower cutoff frequency (Hz)
        - f_high: Upper cutoff frequency (Hz)

        Returns:
        - filtered: Real part of the filtered signal (time domain)
        """
        n = len(signal)
        freqs = np.fft.fftfreq(n, d=1 / fs)
        fft_signal = np.fft.fft(signal)

        # Create mask for bandpass
        mask = (np.abs(freqs) >= f_low) & (np.abs(freqs) <= f_high)
        fft_signal[~mask] = 0

        filtered = np.fft.ifft(fft_signal)
        return filtered.real

    def reset(self):
        self.sampleTimeBuffer.clear()
        self.sampleBuffer.clear()
        self.pulseSignalAvailable = False
        self.totalRecordingTime = 0
        self.averageSamplingRate = float("inf")
        self.averageSamplingFreq = 0
        self.targetMovement = float("inf")
        self.minRRIntervalSamples = (
            self.minRRIntervalDuration / self.processingFramerate
        )


class PPGPulseExtractor(PulseExtractor):
    def __init__(
        self,
        processingFramerate,
        recordingTimeSeconds,
        fingerMovementThreshold,
        maxImageSize,
        frequencyRangeBPM,
        bandpassOrder,
    ):
        super().__init__(
            processingFramerate,
            recordingTimeSeconds,
            fingerMovementThreshold,
            maxImageSize,
            frequencyRangeBPM,
            bandpassOrder,
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
        # return self.totalRecordingTime < self.targetRecordingWindow
        return self.getWindowTime() < self.targetRecordingWindow

    def getWindowTime(self):
        if not self.sampleTimeBuffer:
            return True
        window = np.array(self.sampleTimeBuffer)[
            np.where(
                np.array(self.sampleTimeBuffer) - self.sampleTimeBuffer[-1]
                <= self.targetRecordingWindow
            )
        ]
        return window[-1] - window[0]

    def getPulsePeaks(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        signal = self.getSignal()

        times = np.linspace(0, self.totalRecordingTime, len(signal))
        peakPositions = self.findPeaks(
            signal, threshold=0.5, min_distance=self.minRRIntervalSamples
        )
        if not len(peakPositions):
            return np.array([]), np.array([]), np.array([])
        peakTimes = times[peakPositions]
        peakAmplitudes = signal[peakPositions]

        return peakPositions, peakTimes, peakAmplitudes

    def getBPM(self) -> float:
        # strategy 1 - average RR-interval
        # _, peakMoments, _ = self.getPulsePeaks()
        # RRIntervalDurations = peakMoments[1:] - peakMoments[:-1]
        # averageRRIntervalDuration = np.average(RRIntervalDurations)
        # bpm = 60 / averageRRIntervalDuration

        # strategy 2 - pulses per Window Between Peaks
        # peakPositions,_ , _ = self.getPulsePeaks()
        # bpm=((peakPositions[-1]-peakPositions[0])/(len(peakPositions)-1)*60)

        # strategy 3 - fft
        bpm = self.getPeakFreq(self.getSignal())
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
