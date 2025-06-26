from typing import TypeVar, Callable, ParamSpec
from collections import deque
import numpy as np
import functools
import time

P = ParamSpec("P")
R = TypeVar("R")


class Statistic:
    def __init__(self, bufferMaxLength: int = 32):
        self.buffer: deque[float] = deque(maxlen=bufferMaxLength)
        self.bufferMaxLength: int = bufferMaxLength
        self.lastValue: float = None
        self.minimum: float = None
        self.maximum: float = None
        self.absoluteMinimum: float = None
        self.absoluteMaximum: float = None
        self.average: float = None
        self.absoluteAverage: float = None
        self.count: int = 0

    def addValue(self, value: float):
        self.buffer.append(value)

        self.lastValue = value
        self.minimum = np.min(self.buffer) or self.lastValue
        self.maximum = np.max(self.buffer) or self.lastValue
        self.average = np.average(self.buffer) or self.lastValue
        self.absoluteMaximum = max(
            self.absoluteMaximum or self.lastValue, self.lastValue
        )
        self.absoluteMinimum = max(
            self.absoluteMinimum or self.lastValue, self.lastValue
        )
        self.absoluteAverage = (
            (self.absoluteAverage or self.lastValue) * self.count + value
        ) / (self.count + 1)
        self.count += 1

    def run(self, func: Callable[P, R], *args: P.args, **kwargs: P.kwargs) -> R:
        startTime = time.time()
        returnValue = func(*args, **kwargs)
        self.addValue(time.time() - startTime)
        return returnValue

    def log(self):
        print(f"Last: {self.lastValue}")
        print(f"Minimum: {self.minimum}")
        print(f"Maximum: {self.maximum}")
        print(f"Average: {self.average}")
        print(f"All time average: {self.absoluteAverage}")
        print(f"All time minimum: {self.absoluteMinimum}")
        print(f"All time maximum: {self.absoluteMaximum}")
        print(f"Buffer: {len(self.buffer)}/{self.bufferMaxLength}")


class StatisticsManager:
    Statistics: dict[int, Statistic] = {}
    BUFFER_MAX_LENGTH: int = 32

    @staticmethod
    def ensureKey(key: str, bufferSize: int = None):
        if not key in StatisticsManager.Statistics:
            StatisticsManager.Statistics[key] = Statistic(
                bufferSize or StatisticsManager.BUFFER_MAX_LENGTH
            )
        return StatisticsManager.Statistics[key]

    @staticmethod
    def addValue(key: str, value: float):
        statistic = StatisticsManager.ensureKey(key)
        statistic.addValue(value)

    @staticmethod
    def run(
        key: str,
        func: Callable[P, R],
        defaultBufferSize: int = None,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> R:
        statistic = StatisticsManager.ensureKey(
            key, defaultBufferSize or StatisticsManager.BUFFER_MAX_LENGTH
        )
        res = statistic.run(func, *args, **kwargs)
        StatisticsManager.addValue(key, statistic.lastValue)
        return res

    @staticmethod
    def get(key: str) -> Statistic | None:
        if not key in StatisticsManager.Statistics:
            return None
        return StatisticsManager.Statistics[key]

    @staticmethod
    def log(key: str):
        if key in StatisticsManager.Statistics:
            StatisticsManager.Statistics[key].log()
        else:
            print(f"Missing statistics key {key}")

    @staticmethod
    def clearKey(key: str) -> Statistic:
        return StatisticsManager.Statistics.pop(key, None)

    @staticmethod
    def clear():
        return StatisticsManager.Statistics.clear()


def timedmethod(key: str, bufferSize: int = None):
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            return StatisticsManager.run(key, func, bufferSize, *args, **kwargs)

        return wrapper

    return decorator
