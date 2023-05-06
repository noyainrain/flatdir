# TODO

"""TODO."""

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

from jinja2 import Environment, FileSystemLoader

from .directory import Company, Directory
from .util import color_stream_handler, copy_package

@dataclass
class _Namespace:
    config: str | None

def main() -> int:
    """TODO."""
    logging.basicConfig(
        level=logging.INFO,
        handlers=[color_stream_handler(fmt='%(asctime)s %(levelname)s %(name)s: %(message)s')])
    logger = getLogger(__name__)

    parser = ArgumentParser(
        prog='python3 -m flatdir',
        description='Web aggregator of flat ads from different real estate companies.')
    parser.add_argument('config', nargs='?',
                        help='Path to config file. By default flatdir.ini, if present.')
    args = parser.parse_args(namespace=_Namespace)

    config = ConfigParser(strict=False)
    with resources.open_text('flatdir.res', 'default.ini') as f:
        config.read_file(f)

    config_path: Path | None = Path(args.config or 'flatdir.ini')
    assert config_path
    try:
        with config_path.open(encoding='utf-8') as f:
            config.read_file(f)
    except OSError as e:
        if args.config:
            logger.critical('Failed to load config file %s (%s)', config_path, e.strerror)
            return 1
        config_path = None
    except ParsingError as e:
        logger.critical('Failed to load config file %s (Bad line %d %s)', config_path, *e.errors[0])
        return 1

    companies = []
    for name, options in config.items():
        if name.startswith('company:'):
            try:
                url = options['url']
                company = Company(
                    url, options['ad_path'], options['url_path'], options['title_path'],
                    options['location_path'], options['rooms_path'],
                    location_filter=cast(str, options.get('location_filter', '')))
            except KeyError as e:
                logger.critical('Failed to load config file %s (Missing [%s] %s)', config_path,
                                name, str(e).strip("'"))
                return 1
            except ValueError as e:
                logger.critical('Failed to load config file %s (Relative [%s] url %s)', config_path,
                                name, url)
                return 1
            companies.append(company)

    options = config['flatdir']
    try:
        directory = Directory(companies, title=options['title'], description=options['description'],
                              extra=options['extra'], data_path=options['data_path'])
    except ValueError as e:
        if 'title' in str(e):
            logger.critical('Failed to load config file %s (Blank [flatdir] title)', config_path)
            return 1
        if 'description' in str(e):
            logger.critical('Failed to load config file %s (Blank [flatdir] description)',
                            config_path)
            return 1
        raise

    if config_path:
        logger.info('Loaded config file %s', config_path)

    directory.data_path.mkdir(exist_ok=True)
    directory.update()
    ads = directory.get_ads()

    # ------

    web_path = directory.data_path / 'web'
    web_path.mkdir(exist_ok=True)
    res = resources.files('flatdir.res')
    copy_package(res / 'fonts', web_path / 'fonts')
    copy_package(res / 'images', web_path / 'images')

    # loader = FileSystemLoader('.')
    # TODO PackageLoader
    loader = FileSystemLoader(str(res))
    env = Environment(loader=loader)
    template = env.get_template('template.html')
    index_path = web_path / 'index.html'
    with index_path.open('w', encoding='utf-8') as f:
        f.write(template.render(ads=ads, companies=companies))

    logger.info('Generated %s', index_path)
    return 0

if __name__ == '__main__':
    sys.exit(main())
