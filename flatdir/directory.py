"""TODO."""

from __future__ import annotations

import csv
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from http.client import HTTPResponse
import json
from logging import getLogger
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from urllib.request import urlopen
from typing import cast
from xml.etree.ElementTree import Element

import html5lib
from html5lib import HTMLParser
from html5lib.html5parser import ParseError

class Company:
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

        self._directory: Directory | None = None

    @property
    def directory(self) -> Directory:
        """TODO."""
        if not self._directory:
            raise ValueError('Unset directory')
        return self._directory

    @directory.setter
    def directory(self, value: Directory) -> None:
        if self._directory:
            raise ValueError('Already set directory')
        self._directory = value

    def _parse_html(self, data: bytes) -> list[Ad]:
        # TODO
        return []

    def _parse_json(self, data: bytes) -> list[Ad]:
        # TODO
        return []

    def query(self) -> list[Ad]:
        """TODO."""
        logger = getLogger(__name__)

        def _get_mtime(path: Path) -> datetime | None:
            try:
                return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
            except FileNotFoundError:
                return None

        # TODO just remove ext here, think like: if we had a method get_cache, what would it return:
        # the path and the modified time, but not ext, because that can be extracted
        # or even better like get_mtime_fallback_to_multiple_files(file1, file2, ...):
        #cache_time = None
        #paths = (self.director.data_path / f'{self.host}.json', self.directory.data_path / f'{self.host}.html')
        #for cache_path in paths:
        #    try:
        #        cache_time = ...
        #        break
        #    except FileNotFoundError:
        #        pass

        ext = 'json'
        path = self.directory.data_path / f'{self.host}.{ext}'
        mtime = _get_mtime(path)
        if not mtime:
            ext = 'html'
            path = self.directory.data_path / f'{self.host}.{ext}'
            mtime = _get_mtime(path)

        now = datetime.now(timezone.utc)
        if not mtime or now - mtime > timedelta(minutes=60):
            with cast(HTTPResponse, urlopen(self.url)) as response:
                data = response.read()

            ext = 'html'
            if response.getheader('Content-Type') == 'application/json':
                ext = 'json'

            path = self.directory.data_path / f'{self.host}.{ext}'
            with path.open('wb') as fw:
                fw.write(data)
            logger.info('Fetched %s', self.url)

        with path.open('rb') as f:
            data = f.read()

        if ext == 'json':
            # TODO if this fails - validation error for encoding or not a dict
            result = cast(object, json.loads(data))
            assert isinstance(result, dict)

            def lookup(data: dict[str, object], path: str, typ: type | tuple[type] = str) -> str:
                try:
                    value = data[path]
                except KeyError:
                    raise LookupError(path) from None
                if not isinstance(value, typ):
                    raise LookupError(f'wrong type {type(value).__name__} for {path}')
                return value

            item_data = lookup(result, self.node, typ=list)
            for item in item_data:
                if not isinstance(item, dict):
                    raise LookupError('TODO')
            items = cast(list[dict[str, object]], item_data)
            ## TODO (its okay to parse from data: object because its internal method)
            #def parse_ad(data: object) -> None:
            #def extract_ad(data: object) -> None:
            #    pass

            ads = [
                Ad(
                    # float, int, bool
                    # None
                    # {}, [] => [3, 'lol', True]
                    urljoin(self.url, lookup(item, self.link_node)),
                    lookup(item, self.title_node) or '?',
                    lookup(item, self.location_node),
                    str(lookup(item, self.rooms_node, (str, int))),
                    datetime.now(timezone.utc))
                for item in items]

        else:
            tree = html5lib.parse(data, namespaceHTMLElements=False)
            # Strict parsing fails for 6 of 7 companies lol ;)
            #try:
            #    tree = HTMLParser(strict=True, namespaceHTMLElements=False).parse(data)
            #except ParseError as e:
            #    raise ValueError('Bad HTML') from e

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

from os import PathLike

class Directory:
    """Directory of available flats from different real estate companies.

    .. attribute:: companies

       Source real estate companies.

    .. attribute:: data_directory

       Path to data directory. Must be read- and writable.
    """

    def __init__(self, companies: Iterable[Company], *, data_path: PathLike | str = 'data') -> None:
        self.companies = list(companies)
        for company in companies:
            company.directory = self
        self.data_path = Path(data_path)

    def get_ads(self) -> list[Ad]:
        """Get currently available flats."""
        return [ad for company in self.companies for ad in company.get_ads()]
        #ads = []
        #for company in self.companies:
        #    ads += company.get_ads()
        #return ads

    def update(self) -> None:
        """Aggregate current ads from all :attr:`companies`."""
        logger = getLogger(__name__)
        for company in self.companies:
            try:
                company.update()
            except OSError as e:
                logger.error('Failed to communicate with %s (%s)', company.host, e)
            except ValueError as e:
                logger.error('Bad HTML for %s (%s)', company.host, e.__cause__)
            except LookupError as e:
                logger.error('Failed parse flat ad of %s (%s)', company.host, e)
            except SyntaxError as e:
                logger.error('Bad path for %s (%s)', company.host, e)

# request -> HTML
# parse -> [ads]
# update
# -
# read
# generate
