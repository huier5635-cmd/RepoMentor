from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar


InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")


class BaseWorker(ABC, Generic[InputT, OutputT]):
    worker_name: str

    @abstractmethod
    def run(self, worker_input: InputT) -> OutputT:
        raise NotImplementedError
