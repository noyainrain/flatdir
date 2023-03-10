# TODO

"""TODO."""

from collections.abc import Mapping
import logging
from logging import Formatter, LogRecord
from typing import Literal

ESC = '\x1b'
GREEN = '32'
RED = '31'
DEFAULT = '39'
RESET = '0'

class ColorFormatter(Formatter):
    """TODO."""

    def __init__(
        self, fmt: str | None = None, datefmt: str | None = None,
        style: Literal['%', '{', '$'] = '%', validate: bool = True, *,
        defaults: Mapping[str, object] | None = None
    ) -> None:
        super().__init__(fmt, datefmt, style, validate, defaults=defaults)
        self.colors = {logging.ERROR: RED, logging.INFO: GREEN}

    def format(self, record: LogRecord) -> str:
        s = super().format(record)
        color = self.colors.get(record.levelno, DEFAULT)
        return f'{ESC}[{color}m{s}{ESC}[{RESET}m'
