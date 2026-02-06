from __future__ import annotations

import time
from abc import ABC, abstractmethod


class BaseWatcher(ABC):
    def __init__(self, check_interval: int = 30) -> None:
        self.check_interval = check_interval

    @abstractmethod
    def check(self) -> int:
        """Return number of new items handled."""

    def run(self) -> None:
        while True:
            self.check()
            time.sleep(self.check_interval)
