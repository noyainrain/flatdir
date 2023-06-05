"""Command-Line interface."""

from __future__ import annotations

from argparse import ArgumentParser
from configparser import ConfigParser, ParsingError
from dataclasses import dataclass
from importlib import resources
import logging
from logging import getLogger
from pathlib import Path
import sys
from typing import cast
from urllib.parse import urlsplit

from jinja2 import Environment, PackageLoader

from .directory import Company, Directory
from .util import color_stream_handler, copy_resource

@dataclass
class _Namespace:
    config: str | None = None

def main(*args: str) -> int:
    """Run flatdir with the given command-line *args*."""
    logging.basicConfig(
        level=logging.INFO,
        handlers=[color_stream_handler(fmt='%(asctime)s %(levelname)s %(name)s: %(message)s')])
    logger = getLogger(__name__)

    parser = ArgumentParser(
        prog='python3 -m flatdir',
        description='Aggregate flat ads from different real estate companies.')
    parser.add_argument('config', nargs='?',
                        help='Path to config file. By default flatdir.ini, if present.')
    ns = parser.parse_args(args[1:], namespace=_Namespace())

    res = resources.files(f'{__package__}.res')
    config = ConfigParser(strict=False)
    with (res / 'default.ini').open(encoding='utf-8') as f:
        config.read_file(f)

    config_path: Path | None = Path(ns.config or 'flatdir.ini')
    assert config_path
    try:
        with config_path.open(encoding='utf-8') as f:
            config.read_file(f)
    except OSError as e:
        if ns.config:
            logger.critical('Failed to load config file %s (%s)', config_path, e.strerror)
            return 1
        config_path = None
    except ParsingError as e:
        number, line = e.errors[0]
        logger.critical('Failed to load config file %s (Bad line %d %s)', config_path, number,
                        line.strip("'"))
        return 1

    companies = []
    for name, options in config.items():
        if name.startswith('company:'):
            try:
                rooms_optional = options.getboolean('rooms_optional', False)
            except ValueError:
                logger.critical('Failed to load config file %s ([%s] Bad rooms_optional type)',
                                config_path, name)
                return 1
            try:
                company = Company(
                    options['url'], options['ad_path'], options['url_path'], options['title_path'],
                    options['location_path'], options['rooms_path'], rooms_optional=rooms_optional,
                    location_filter=cast(str, options.get('location_filter', '')))
            except KeyError as e:
                logger.critical('Failed to load config file %s ([%s] Missing %s)', config_path,
                                name, str(e).strip("'"))
                return 1
            except ValueError as e:
                logger.critical('Failed to load config file %s ([%s] %s)', config_path, name, e)
                return 1
            companies.append(company)

    options = config['flatdir']
    try:
        directory = Directory(companies, title=options['title'], description=options['description'],
                              extra=options['extra'], data_path=options['data_path'])
    except ValueError as e:
        logger.critical('Failed to load config file %s ([flatdir] %s)', config_path, e)
        return 1
    url = options['url']
    components = urlsplit(url)
    if not (components.scheme and components.hostname):
        logger.critical('Failed to load config file %s ([flatdir] Relative url %s)', config_path,
                        url)
        return 1

    if config_path:
        logger.info('Loaded config file %s', config_path)

    templates = Environment(autoescape=True, loader=PackageLoader(f'{__package__}.res', '.'))
    template = templates.get_template('template.html')

    try:
        directory.data_path.mkdir(exist_ok=True)
        directory.update()

        web_path = directory.data_path / 'web'
        web_path.mkdir(exist_ok=True)
        copy_resource(res / 'fonts', web_path / 'fonts')
        copy_resource(res / 'images', web_path / 'images')
        html = template.render(directory=directory, companies=companies, ads=directory.get_ads(),
                               url=url)
        index_path = web_path / 'index.html'
        index_path.write_text(html)
    except OSError as e:
        logger.critical('Failed to access data directory (%s)', e.strerror)
        return 2

    logger.info('Generated web directory %s', index_path)
    return 0

sys.exit(main(*sys.argv))
