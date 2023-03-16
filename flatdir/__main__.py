# TODO

import logging
from logging import getLogger, StreamHandler
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from .directory import Directory
from .companies import COMPANIES

from .util import ColorFormatter, color_stream_handler

def main() -> None:
    """TODO."""

    #logging.basicConfig(level=logging.DEBUG,
    #                    format='%(asctime)s %(levelname)s %(name)s: %(message)s')
    logging.basicConfig(
        level=logging.DEBUG,
        handlers=[color_stream_handler(fmt='%(asctime)s %(levelname)s %(name)s: %(message)s')])
    logger = getLogger(__name__)

    #logger.debug('Fetched document')
    #logger.info('Updated ads')
    #logger.warning('Unknown configuration key')
    #logger.error('Failed to fetch document')
    #try:
    #    raise ValueError()
    #except ValueError:
    #    logger.exception('Unhandled error')
    #logger.critical('Failed to access data directory')
    #return

    data_path = Path('data')
    data_path.mkdir(exist_ok=True)

    directory = Directory(COMPANIES, data_path=data_path)
    directory.update()
    ads = directory.get_ads()

    loader = FileSystemLoader('.')
    env = Environment(loader=loader)
    template = env.get_template('template.html')
    with Path('index.html').open('w', encoding='utf-8') as f:
        f.write(template.render(ads=ads, companies=COMPANIES))

    logger.info('Generated index.html')

if __name__ == '__main__':
    main()
