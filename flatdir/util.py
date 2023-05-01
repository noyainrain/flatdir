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
from importlib.abc import Traversable
import logging
from logging import Formatter, LogRecord, StreamHandler
from os import PathLike
from pathlib import Path
import sys
from typing import Literal, TextIO, TypeVar, cast, overload
from xml.etree.ElementTree import Element

SELECT_GRAPHIC_RENDITION = 'm'
NORMAL = 0
FOREGROUND = 30

_FormatStyle = Literal['%', '{', '$']

_T = TypeVar('_T')
_U = TypeVar('_U')

# p = dest / src.name # should have the same behaviour as below

def copy_package(src: Traversable, dest: PathLike[str] | str) -> None:
    """TODO."""
    #if dest.is_dir():
    #    dest /= src.name
    dest = Path(dest)

    if src.is_dir():
        #print('MKDIR', dest)
        dest.mkdir(exist_ok=True)
        for child in src.iterdir():
            copy_package(child, dest / child.name)
        return

    #print('COPY', src, 'TO', dest)
    dest.write_bytes(src.read_bytes())

    #with src.open('rb') as fin:
    #    print('COPY', src, 'TO', new_path)
    #    with dest.open('wb') as fout:
    #        fout.write(fin.read())
    #    # new_path = root / rel
    #    # new_path = dest
    #    #if dest.is_dir():
    #    #    new_path = dest / src.name
    #    #if not dest.parent.exists(): # OQ
    #    #    print('CREATING PARENT DIR', dest.parent)
    #    #    dest.parent.mkdir(parents=True)

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

def query_xml(node: Element, path: str) -> list[Element]:
    """TODO."""
    segments = path.split('/')
    leaf: str | None = segments.pop()
    assert leaf
    if not (leaf.startswith('@') or leaf == 'tail()'):
        segments.append(leaf)
        leaf = None
    nodes = node.findall('/'.join(segments))

    def get_leaf(node: Element, leaf: str | None) -> Element | None:
        if leaf is None:
            return node
        if leaf.startswith('@'):
            name = leaf[1:]
            text = node.get(name)
            if text is None:
                return None
            pseudo = Element(name)
            pseudo.text = text
            return pseudo
            # return None if text is None else Element(name, text=text)
        if leaf == 'tail()':
            if node.tail is None:
                return None
            pseudo = Element('#text')
            pseudo.text = node.tail
            return pseudo
            # return None if node.tail is None else Element('#text', text=node.tail)
        assert False

    return [x for node in nodes if (x := get_leaf(node, leaf)) is not None]


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
    style: _FormatStyle = '%', validate: bool = True,
    colors: Mapping[int, Color] = ColorFormatter.DEFAULT_COLORS
) -> 'StreamHandler[TextIO]':
    """Return a stream log handler using :cls:`ColorFormatter`.

    If *stream* is not connected to a terminal, the standard :cls:`Formatter` is used.
    """
    # pylint: disable=dangerous-default-value
    handler = StreamHandler(stream)
    formatter = (ColorFormatter(fmt, datefmt, style, validate, colors=colors) if stream.isatty()
                 else Formatter(fmt, datefmt, style, validate))
    handler.setFormatter(formatter)
    return handler
