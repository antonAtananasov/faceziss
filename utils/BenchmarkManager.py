from utils.CVUtils import FRAMERATE_ENUM, HAARCASCADE_ENUM, RESOLUTION_ENUM
from utils.EncryptionManager import ENCRYPTION_ALGORITHM_ENUM
from utils.FaceDetector import EMBEDDING_ALGORITHM_ENUM
from utils.StatisticsManager import StatisticsManager
from cv2.typing import MatLike


class BenchmarkManager:
    def __init__(self):
        self.statisticsManager = StatisticsManager()

    def runEncryptionBenchmark(
        self,
        algorithm: ENCRYPTION_ALGORITHM_ENUM,
        data: list[float],
        timeoutSeconds: float,
    ):
        raise NotImplementedError()

    def runClassificationBenchmark(
        self, classifier: HAARCASCADE_ENUM, images: list[MatLike], timeoutSeconds: float
    ):
        raise NotImplementedError()

    def runEmbeddingBenchmark(
        self,
        classifier: EMBEDDING_ALGORITHM_ENUM,
        images: list[MatLike],
        timeoutSeconds: float,
    ):
        raise NotImplementedError()

    def runPPGBenchmark(self, images: list[MatLike], timeoutSeconds: float):
        raise NotImplementedError()

    def runEVMBenchmark(
        self,
        freqRange: tuple[float, float],
        images: list[MatLike],
        timeoutSeconds: float,
    ):
        raise NotImplementedError()

    def runPreviewBenchmark(
        self, resolution: RESOLUTION_ENUM, framerate: FRAMERATE_ENUM, timeout: float
    ):
        raise NotImplementedError()
