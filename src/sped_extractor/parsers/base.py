from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterable, List, Sequence

from ..config import encodings
from ..utils import try_decode

LOGGER = logging.getLogger(__name__)


class Parser(ABC):
    def __init__(self) -> None:
        self.logger = LOGGER.getChild(self.__class__.__name__)

    @abstractmethod
    def applicable(self, content: bytes) -> bool:
        """Heuristically decide whether this parser can handle the payload."""

    @abstractmethod
    def parse(self, path: Path, content: bytes) -> List[dict]:
        """Transform the file into item-level dictionaries."""

    def read_lines(self, content: bytes) -> Sequence[str]:
        decoded = try_decode(content, encodings.preferred)
        return decoded.splitlines()

    def info(self, message: str, *args) -> None:
        self.logger.info(message, *args)

    def warning(self, message: str, *args) -> None:
        self.logger.warning(message, *args)

    def debug(self, message: str, *args) -> None:
        self.logger.debug(message, *args)

