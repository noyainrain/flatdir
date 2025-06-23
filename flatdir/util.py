"""Various utilities.

.. data:: SELECT_GRAPHIC_RENDITION

   Select Graphic Rendition ANSI control function.

.. data:: NORMAL

   Normal graphic rendition.

.. data:: FOREGROUND

   Custom foreground color graphic rendition.
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import Enum
from itertools import chain
import logging
from logging import Formatter, LogRecord, StreamHandler
from os import PathLike
from pathlib import Path
import sys
from typing import Iterable, Literal, TextIO, TypeVar, cast, overload
from xml.etree.ElementTree import Element

if sys.version_info < (3, 11):
    # Work around Pylint rejecting deprecated features in compatibility code (see
    # https://github.com/pylint-dev/pylint/issues/9533)
    # pylint: disable=deprecated-class
    from importlib.abc import Traversable
else:
    from importlib.resources.abc import Traversable

FormatStyle = Literal['%', '{', '$']

T = TypeVar('T')
U = TypeVar('U')
V = TypeVar('V')

SELECT_GRAPHIC_RENDITION = 'm'
NORMAL = 0
FOREGROUND = 30

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
        self, fmt: str | None = None, datefmt: str | None = None, style: FormatStyle = '%',
        validate: bool = True, *, colors: Mapping[int, Color] = DEFAULT_COLORS,
    ) -> None:
        # pylint: disable=dangerous-default-value
        super().__init__(fmt, datefmt, style, validate)
        self.colors = dict(colors)

    def format(self, record: LogRecord) -> str:
        message = super().format(record)
        foreground = self.colors.get(record.levelno, Color.DEFAULT).value + FOREGROUND
        return (f'{control_sequence(SELECT_GRAPHIC_RENDITION, foreground)}{message}'
                f'{control_sequence(SELECT_GRAPHIC_RENDITION, NORMAL)}')

def color_stream_handler(
    stream: TextIO = sys.stderr, *, fmt: str | None = None, datefmt: str | None = None,
    style: FormatStyle = '%', validate: bool = True,
    colors: Mapping[int, Color] = ColorFormatter.DEFAULT_COLORS
) -> StreamHandler[TextIO]:
    """Return a stream log handler using :cls:`ColorFormatter`.

    If *stream* is not connected to a terminal, the standard :cls:`logging.Formatter` is used.
    """
    # pylint: disable=dangerous-default-value
    handler = StreamHandler(stream)
    formatter = (ColorFormatter(fmt, datefmt, style, validate, colors=colors) if stream.isatty()
                 else Formatter(fmt, datefmt, style, validate))
    handler.setFormatter(formatter)
    return handler

def control_sequence(func: str, arg: int) -> str:
    """Return an ANSI control sequence for the function *func* with the argument *arg*."""
    # See https://en.wikipedia.org/wiki/ANSI_escape_code#CSI_(Control_Sequence_Introducer)_sequences
    return f'\x1b[{arg}{func}'

def copy_resource(src: Traversable, dst: PathLike[str] | str) -> None:
    """Copy the resource or resource container *src* to the file or directory *dst*.

    An :exc:`OSError` is raised if there is any problem accessing *src* or *dst*.
    """
    dst = Path(dst)
    if src.is_dir():
        dst.mkdir(exist_ok=True)
        for child in src.iterdir():
            copy_resource(child, dst / child.name)
    else:
        dst.write_bytes(src.read_bytes())

@overload
def query_json(value: object, path: str) -> list[object]:
    pass
@overload
def query_json(value: object, path: str, cls: type[T]) -> list[T]:
    pass
@overload
def query_json(value: object, path: str, cls: tuple[type[T], type[U]]) -> list[T | U]:
    pass
@overload
def query_json(value: object, path: str, cls: tuple[type[T], type[U], type[V]]) -> list[T | U | V]:
    pass
def query_json(
    value: object, path: str,
    cls: type[T] | tuple[type[T], type[U]] | tuple[type[T], type[U], type[V]] | None = None
) -> list[object] | list[T] | list[T | U] | list[T | U | V]:
    """Query all items of the JSON collection *value* matching *path*.

    *path* is a dotted path, where `*` matches all items of a collection. If *path* cannot be
    followed, a :exc:`LookupError` is raised. Optionally, if the queried values are not of the type
    *cls*, a :exc:`ValueError` is raised.
    """
    def query(value: object, name: str) -> Iterable[object]:
        if isinstance(value, dict):
            obj = cast(dict[str, object], value)
            # LookupError is passed through
            return obj.values() if name == '*' else (obj[name], )
        if isinstance(value, list):
            array = cast(list[object], value)
            try:
                return array if name == '*' else (array[int(name)], )
            except (IndexError, ValueError):
                raise LookupError(name) from None
        raise LookupError(name)

    items = [value]
    for name in path.split('.'):
        items = list(chain.from_iterable(query(item, name) for item in items))

    if cls:
        for item in items:
            if not isinstance(item, cls):
                raise ValueError(f'Bad item type {type(item).__name__} at {path}')
    return items

def query_xml(element: Element, path: str) -> list[Element]:
    """Query all children of the XML *element* matching *path*.

    *path* is a simplified XPath expression (see
    https://docs.python.org/3/library/xml.etree.elementtree.html#supported-xpath-syntax).

    Additionally, the last segment may specify a pseudo-element:

    * `@name` selects the attribute with *name*
    * `tail()` selects the text immediately following the element
    """
    pseudo = None
    segments = path.split('/')
    final = segments[-1]
    if final.startswith('@') or final == 'tail()':
        pseudo = final
        segments.pop()

    def query_pseudo(element: Element, pseudo: str | None) -> Element | None:
        if pseudo is None:
            return element
        if pseudo.startswith('@'):
            name = pseudo[1:]
            text = element.get(name)
            if text is None:
                return None
            result = Element(name)
            result.text = text
            return result
        if pseudo == 'tail()':
            if element.tail is None:
                return None
            result = Element('#text')
            result.text = element.tail
            return result
        assert False

    try:
        children = element.findall('/'.join(segments))
    except SyntaxError as e:
        raise SyntaxError(f'Bad path {path}') from e
    return [result for child in children if (result := query_pseudo(child, pseudo)) is not None]
