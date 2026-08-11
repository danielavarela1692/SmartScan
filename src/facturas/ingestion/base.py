from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterator


@dataclass
class RawDocument:
    filename: str
    content: bytes
    origin: str


class Source(ABC):
    @abstractmethod
    def fetch_new(self) -> Iterator[RawDocument]:
        """Yield documents not returned by a previous call."""
