"""TODO."""

from __future__ import annotations

import csv
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from http.client import HTTPResponse
import json
import logging
from logging import getLogger
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from urllib.request import urlopen
from typing import cast
from xml.etree.ElementTree import Element

import html5lib
from jinja2 import Environment, FileSystemLoader

class Broker:
    """TODO."""

    def __init__(self, url: str, node: str, link_node: str, title_node: str, location_node: str,
                 rooms_node: str, *, location_filter: str | None = None) -> None:
        self.url = url
        self.host = urlsplit(url).hostname
        if not self.host:
            raise ValueError(f'Bad URL {url}')
        self.node = node
        self.link_node = link_node
        self.title_node = title_node
        self.location_node = location_node
        self.rooms_node = rooms_node
        self.location_filter = location_filter

    def query(self) -> list[Ad]:
        """TODO."""
        logger = getLogger(__name__)

        def _get_mtime(path: Path) -> datetime | None:
            try:
                return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
            except FileNotFoundError:
                return None

        ext = 'json'
        path = Path(f'data/{self.host}.{ext}')
        mtime = _get_mtime(path)
        if not mtime:
            ext = 'html'
            path = Path(f'data/{self.host}.{ext}')
            mtime = _get_mtime(path)

        now = datetime.now(timezone.utc)
        if not mtime or now - mtime > timedelta(minutes=60):
            with cast(HTTPResponse, urlopen(self.url)) as response:
                data = response.read()

            ext = 'html'
            if response.getheader('Content-Type') == 'application/json':
                ext = 'json'

            path = Path(f'data/{self.host}.{ext}')
            with path.open('wb') as fw:
                fw.write(data)
            logger.info('Fetched %s', self.url)

        with path.open('rb') as f:
            data = f.read()

        if ext == 'json':
            result = json.loads(data)
            items = result[self.node]
            ads = [
                Ad(
                    urljoin(self.url, item[self.link_node]),
                    item[self.title_node],
                    item[self.location_node],
                    item[self.rooms_node],
                    datetime.now(timezone.utc))
                for item in items]

        else:
            tree = html5lib.parse(data, namespaceHTMLElements=False)

            def find_node(elem: Element, path: str) -> Element:
                node = elem.find(path)
                if node is None:
                    raise LookupError(path, f"<{elem.tag} {' '.join('='.join(x) for x in elem.attrib.items())}>")
                return node

            def select(elem: Element, path: str) -> str:
                mode = 'text'
                if path.endswith('/tail()'):
                    mode = 'tail'
                    path = path[:-7]

                node = elem.find(path)
                if node is None:
                    raise LookupError(path, f"<{elem.tag} {' '.join('='.join(x) for x in elem.attrib.items())}>")

                if mode == 'tail':
                    return node.tail or ''
                return node.text or ''

            nodes = tree.findall(self.node)
            ads = [
                Ad(
                    urljoin(self.url, find_node(node, self.link_node).get('href')),
                    (find_node(node, self.title_node).text or '?').strip(),
                    (find_node(node, self.location_node).text or '?').strip(),
                    # int((find_node(node, self.rooms_node).tail or '').strip() or '0'),
                    # (find_node(node, self.rooms_node).tail or '').strip() or '?',
                    select(node, self.rooms_node).strip() or '',
                    datetime.now(timezone.utc))
                for node in nodes]

        ads = [ad for ad in ads if ad.rooms]
        if self.location_filter:
            ads = [ad for ad in ads if self.location_filter in ad.location]

        #for ad in ads:
        #    print('AD ROOMS', ad.rooms)

        # logger.info('Received %d ad(s) from %s', len(ads), self.host)

        return ads

    def update(self) -> None:
        """TODO."""
        logger = getLogger(__name__)

        old_ads = {ad.url: ad for ad in self.get_ads()}

        ads = self.query()
        for ad in ads:
            if old_ad := old_ads.get(ad.url):
                # print('OVERWRITING TIME', ad.time, '->', old_ad.time, ad.url)
                ad.time = old_ad.time

        path = Path(f'data/{self.host}.csv')
        with path.open('w', encoding='utf-8') as f:
            writer = csv.DictWriter(f, ['url', 'title', 'location', 'rooms', 'time'])
            writer.writeheader()
            for ad in ads:
                # row = [ad.url, ad.title, ad.location, ad.time.isoformat()]
                row = {'url': ad.url, 'title': ad.title, 'location': ad.location, 'rooms': ad.rooms,
                       'time': ad.time.isoformat()}
                writer.writerow(row)

        logger.info('Updated %d ad(s) from %s', len(ads), self.host)

    def get_ads(self) -> list[Ad]:
        """TODO."""
        path = Path(f'data/{self.host}.csv')
        try:
            with path.open(encoding='utf-8') as f:
                return [
                    Ad(row['url'], row['title'], row['location'], row['rooms'],
                       datetime.fromisoformat(row['time']))
                    for row in cast(Iterable[dict[str, str]], csv.DictReader(f))]
        except FileNotFoundError:
            return []

@dataclass
class Ad:
    """TODO."""

    url: str
    title: str
    location: str
    rooms: str
    time: datetime

    def __post_init__(self) -> None:
        self.host = urlsplit(self.url).hostname
        if not self.host:
            raise ValueError(f'Bad URL {self.url}')

# TODO rename Company()
BROKERS = [
    # Brokers
    #Broker(
    #    'https://www.schacher-immobilien.de/angebote/wohnungen/?mt=67555823520346',
    #    ".//*[@class='listEntry listEntryClickable listEntryObject-immoobject listEntryObject-immoobject_var']",
    #    'div/div[2]/div[2]/a',
    #    'div/div[2]/div[2]/a',
    #    'div/div[2]/div',
    #    '.',
    #    location_filter='Berlin'),

    Broker(
        'https://werneburg-immobilien.de/immobilien/immobilien-vermarktungsart/miete/',
        ".//div[@class='property col-sm-6 col-md-4']",
        'div/div[2]/h3/a',
        'div/div[2]/h3/a',
        'div/div[2]/div',
        'div/div[2]/div[2]/div[2]/div[2]',
        location_filter='Berlin'),

    Broker(
        'https://www.homesk.de/Rent/RentalFlats',
        ".//a[@class='tile tile-sm-640px-480px tile-md-960px-480px tile-lg-1280px-480px']",
        '.',
        'div/div/div[2]/div/div/div/div/h3',
        'div/div/div[2]/div/div/div/div/p',
        'div/div/div[2]/div/div/div/div[2]/div/div/h4'),

    # Property managers
    Broker(
        'https://www.berlinhaus.com/suchergebnisse/?filter_search_action[]=wohnen&advanced_city=berlin&zimmeranzahl-ab=1',
        ".//div[@class='col-md-12 listing_wrapper']",
        'div/h4/a',
        'div/h4/a',
        'div/div[2]/a',
        'div/div[4]/div[2]'),

    Broker(
        url='https://www.gesobau.de/mieten/wohnungssuche.html',
        # node=".//div[@class='list_item']",
        # node=".//div[@data-id]",
        node=".//div[@id='tx-openimmo-6329']/div[2]/div[1]/div/div[1]/div",
        link_node='div/div/h3/a',
        title_node='div/div/h3/a',
        location_node='div/div/div[1]',
        rooms_node='div/div/div[2]/div[3]'
    ),

    Broker(
        'https://www.howoge.de/?type=999&tx_howsite_json_list[action]=immoList',
        'immoobjects',
        'link',
        'title',
        'district',
        'rooms'
        # 'https://www.howoge.de/wohnungen-gewerbe/wohnungssuche.html',
        #".//div[@class='flat-single']",
        #'div[2]/div[3]/a',
        #'div[2]/div[3]/a',
        #'div[2]/div[2]',
        #'div[2]/div[4]/div/div/div[3]/div[2]'
    ),

    Broker(
        url='https://www.kurtzke-immobilien.de/objekttyp/mietwohnung/',
        node=".//div[@class='item-listing-wrap hz-item-gallery-js card']",
        link_node='div/div/div[2]/h2/a',
        title_node='div/div/div[2]/h2/a',
        location_node='div/div/div[2]/address',
        rooms_node='div/div/div[2]/ul/li/span[2]'
    ),

    Broker(
        'https://www.livinginberlin.de/angebote/mieten',
        ".//div[@class='uk-container uk-margin-large-top uk-margin-medium-bottom']/div/div",
        'div/div/a',
        'div/div[2]/p',
        'div/div[2]/h3',
        'div/div[2]/span/tail()',
        location_filter='Berlin'
    )
]

# request -> HTML
# parse -> [ads]
# update
# -
# read
# generate

def main() -> None:
    """TODO."""
    logging.basicConfig(level=logging.INFO)
    logger = getLogger(__name__)

    Path('data').mkdir(exist_ok=True)

    ads = []
    for broker in BROKERS:
        broker.update()
        ads += broker.get_ads()

    loader = FileSystemLoader('.')
    env = Environment(loader=loader)
    template = env.get_template('template.html')
    with Path('index.html').open('w', encoding='utf-8') as f:
        f.write(template.render(ads=ads, companies=BROKERS))

    logger.info('Generated index.html')

if __name__ == '__main__':
    main()
