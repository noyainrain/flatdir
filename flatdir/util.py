"""Various utilities.

.. data:: SELECT_GRAPHIC_RENDITION

   Select Graphic Rendition ANSI control function.

.. data:: NORMAL

   Normal graphic rendition.

.. data:: FOREGROUND

   Custom foreground color graphic rendition.
"""

from collections.abc import Mapping
from enum import Enum
import logging
from logging import Formatter, LogRecord, StreamHandler
import sys
from typing import Literal, TextIO, TypeVar, overload

SELECT_GRAPHIC_RENDITION = 'm'
NORMAL = 0
FOREGROUND = 30

_FormatStyle = Literal['%', '{', '$']

_T = TypeVar('_T')
_U = TypeVar('_U')

from typing import cast

@overload
def query_json(obj: dict[str, object], path: str) -> list[object]:
    pass
@overload
def query_json(obj: dict[str, object], path: str, typ: type[_T]) -> list[_T]:
    pass
@overload
def query_json(obj: dict[str, object], path: str, typ: tuple[type[_T], type[_U]]) -> list[_T | _U]:
    pass
def query_json(
    obj: dict[str, object], path: str, typ: type[_T] | tuple[type[_T], type[_U]] | None = None
) -> list[object] | list[_T] | list[_T | _U]:
    """TODO."""
    tokens = path.split('.')
    values: list[object] = [obj]
    for token in tokens:
        level = []
        for value in values:
            if isinstance(value, dict):
                obj = value
                if token == '*':
                    level += list(obj.values())
                else:
                    # LookupError passed through
                    level.append(obj[token])
            elif isinstance(value, list):
                array = cast(list[object], value)
                if token == '*':
                    level += array
                else:
                    try:
                        level.append(array[int(token)])
                    except (IndexError, ValueError):
                        raise LookupError(token) from None
            else:
                # NOTE could add path information here
                # raise ValueError(f'Bad value type {type(value)}')
                raise LookupError(token)
        values = level

    if typ:
        for value in values:
            if not isinstance(value, typ):
                raise LookupError('BAD TYPE TODO')
    return values

# objects = [{'foo': {}}]
# tokens = 'foo.*.*'.split('.')
# for token in tokens:
#     new = []
#     for obj in objects:
#         keys = [token]
#         if token == '*':
#             keys = obj.keys()
#         for key in keys:
#             new.append(obj[key])
#     objects = new

class Color(Enum):
    """ANSI terminal color."""
    BLACK = 0
    RED = 1
    GREEN = 2
    YELLOW = 3
    BLUE = 4
    MAGENTA = 5
    CYAN = 6
    WHITE = 7
    DEFAULT = 9

def control_sequence(func: str, arg: int) -> str:
    """Return an ANSI control sequence for the function *func* with the argument *arg*."""
    # See https://en.wikipedia.org/wiki/ANSI_escape_code#CSI_(Control_Sequence_Introducer)_sequences
    return f'\x1b[{arg}{func}'

class ColorFormatter(Formatter):
    """ANSI terminal log message formatter that colors messages by log level.

    .. attr: colors

       Log level colors.

    .. attr: DEFAULT_COLORS

       Default log level colors.
    """

    DEFAULT_COLORS = {
        logging.INFO: Color.GREEN,
        logging.WARNING: Color.YELLOW,
        logging.ERROR: Color.RED,
        logging.CRITICAL: Color.MAGENTA
    }

    def __init__(
        self, fmt: str | None = None, datefmt: str | None = None, style: _FormatStyle = '%',
        validate: bool = True, *, colors: Mapping[int, Color] = DEFAULT_COLORS,
    ) -> None:
        super().__init__(fmt, datefmt, style, validate)
        self.colors = dict(colors)

    def format(self, record: LogRecord) -> str:
        message = super().format(record)
        foreground = self.colors.get(record.levelno, Color.DEFAULT).value + FOREGROUND
        return (f'{control_sequence(SELECT_GRAPHIC_RENDITION, foreground)}{message}'
                f'{control_sequence(SELECT_GRAPHIC_RENDITION, NORMAL)}')

def color_stream_handler(
    stream: TextIO = sys.stderr, *, fmt: str | None = None, datefmt: str | None = None,
    style: _FormatStyle = '%', validate: bool = True,
    colors: Mapping[int, Color] = ColorFormatter.DEFAULT_COLORS
) -> 'StreamHandler[TextIO]':
    """Return a stream log handler using :cls:`ColorFormatter`.

    If *stream* is not connected to a terminal, the standard :cls:`Formatter` is used.
    """
    handler = StreamHandler(stream)
    formatter = (ColorFormatter(fmt, datefmt, style, validate, colors=colors) if stream.isatty()
                 else Formatter(fmt, datefmt, style, validate))
    handler.setFormatter(formatter)
    return handler
