import time
from typing import TypeVar, Callable, ParamSpec
import numpy as np
from collections import deque 

P = ParamSpec("P")
R = TypeVar("R")


class MyStatistic:
    def __init__(self, bufferMaxLength: int = 32):
        self.buffer = deque(maxlen=bufferMaxLength)
        self.bufferMaxLength = bufferMaxLength
        self.lastValue = None
        self.minimum = None
        self.maximum = None
        self.absoluteMinimum = None
        self.absoluteMaximum = None
        self.average = None
        self.absoluteAverage = None
        self.count = 0

    def newValue(self, value: float):
        self.buffer.append(value)

        self.lastValue = value
        self.minimum = np.min(self.buffer) or self.lastValue
        self.maximum = np.max(self.buffer) or self.lastValue
        self.average = np.average(self.buffer) or self.lastValue
        self.absoluteMaximum = max(self.absoluteMaximum or self.lastValue, self.lastValue)
        self.absoluteMinimum = max(self.absoluteMinimum or self.lastValue, self.lastValue)
        self.absoluteAverage = (
            (self.absoluteAverage or self.lastValue) * self.count + value
        ) / (self.count + 1)
        self.count += 1

    def run(self, func: Callable[P, R], *args: P.args, **kwargs: P.kwargs) -> R:
        startTime = time.time()
        returnValue = func(*args, **kwargs)
        self.newValue(time.time() - startTime)
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


class MyStatistics:
    def __init__(self, bufferMaxLength: int = 32):
        self.statistics: dict[str, MyStatistic] = {}
        self.bufferMaxLength = bufferMaxLength

    def _ensureKey(self, key):
        if not key in self.statistics:
            self.statistics[key] = MyStatistic(self.bufferMaxLength)

    def newValue(self, key: str, value: float):
        self._ensureKey(key)
        self.statistics[key].newValue(value)

    def run(
        self, key: str, func: Callable[P, R], *args: P.args, **kwargs: P.kwargs
    ) -> R:
        self._ensureKey(key)
        if not key in self.statistics:
            self.statistics[key] = MyStatistic(self.bufferMaxLength)

        return self.statistics[key].run(func, *args, **kwargs)
    
    def log(self, key:str):
        if key in self.statistics:
            self.statistics[key].log()
        else:
            print(f'Missing statistics key {key}')
