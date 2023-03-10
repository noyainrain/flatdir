# TODO

import logging
from logging import getLogger, StreamHandler
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from .directory import BROKERS

from .util import ColorFormatter

def main() -> None:
    """TODO."""

    handler = StreamHandler()
    handler.setFormatter(ColorFormatter('%(levelname)s:%(name)s:%(message)s'))
    logging.basicConfig(level=logging.INFO, handlers=[handler])

    # logging.basicConfig(level=logging.INFO)
    logger = getLogger(__name__)

    Path('data').mkdir(exist_ok=True)

    ads = []
    for broker in BROKERS:
        try:
            broker.update()
        except OSError as e:
            logger.error('Failed to communicate with %s (%s)', broker.host, e)
        except ValueError as e:
            logger.error('Bad HTML for %s (%s)', broker.host, e.__cause__)
        except LookupError as e:
            logger.error('Failed parse flat ad of %s (%s)', broker.host, e)
        except SyntaxError as e:
            logger.error('Bad path for %s (%s)', broker.host, e)
        ads += broker.get_ads()

    loader = FileSystemLoader('.')
    env = Environment(loader=loader)
    template = env.get_template('template.html')
    with Path('index.html').open('w', encoding='utf-8') as f:
        f.write(template.render(ads=ads, companies=BROKERS))

    logger.info('Generated index.html')

if __name__ == '__main__':
    main()
