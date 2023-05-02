# TODO

"""TODO."""

from __future__ import annotations

import csv
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta
from http.client import HTTPResponse
import json
from logging import getLogger
from os import PathLike
from pathlib import Path
import re
from typing import TypeVar, cast, overload
from urllib.parse import urljoin, urlsplit
from urllib.request import urlopen
from xml.etree.ElementTree import Element

import html5lib

from .util import query_json, query_xml

ONLINE_THRESHOLD = timedelta(hours=1, minutes=30)
# ONLINE_THRESHOLD = timedelta(hours=0, minutes=1)

_T = TypeVar('_T')
_U = TypeVar('_U')

@dataclass
class Ad:
    """Flat ad.

    .. attribute:: url

       URL of the ad.

    .. attribute:: title

       Title of the ad.

    .. attribute:: location

       Location of the flat.

    .. attribute:: rooms

       Number of rooms of the flat.

    .. attribute:: time

       TODO.
    """

    url: str
    title: str
    location: str
    rooms: float
    time: datetime

    def __post_init__(self) -> None:
        self.host = urlsplit(self.url).hostname
        if not self.host:
            raise ValueError(f'Bad URL {self.url}')

class Company:
    """Real estate company.

    .. attribute:: url

       URL of the document containing currently available flats of the company.

    .. attribute:: ad_path

       Path matching all ads in the document.

    .. attribute:: url_path

       Subpath to the URL of an ad.

    .. attribute:: title_path

       Subpath to the title of an ad.

    .. attribute:: location_path

       Subpath to the location of a flat.

    .. attribute:: rooms_path

       Subpath to the number of rooms of a flat.

    .. attribute:: location_filter

       Term that the location of a flat needs to contain to be included.
    """

    def __init__(self, url: str, ad_path: str, url_path: str, title_path: str, location_path: str,
                 rooms_path: str, *, location_filter: str = '') -> None:
        components = urlsplit(url)
        if not (components.scheme and components.hostname):
            raise ValueError(f'Relative url {url}')
        self.url = url
        self.host = components.hostname
        self.ad_path = ad_path
        self.url_path = url_path
        self.title_path = title_path
        self.location_path = location_path
        self.rooms_path = rooms_path
        self.location_filter = location_filter

        self._directory: Directory | None = None
        self._ads_path = Path()

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
        self._ads_path = self.directory.data_path / f'{self.host}.csv'

    def is_ok(self) -> bool:
        """TODO."""
        try:
            return (self.directory.now() - datetime.fromtimestamp(self._ads_path.stat().st_mtime)
                    < ONLINE_THRESHOLD)
        except FileNotFoundError:
            return False

    def _parse_html(self, data: bytes) -> list[Ad]:
        # TODO
        tree = html5lib.parse(data, namespaceHTMLElements=False)
        # Strict parsing fails for 6 of 7 companies lol ;)
        #try:
        #    tree = HTMLParser(strict=True, namespaceHTMLElements=False).parse(data)
        #except ParseError as e:
        #    raise ValueError('Bad HTML') from e

        def select(elem: Element, path: str) -> str:
            try:
                node = query_xml(elem, path)[0]
            except IndexError:
                # TODO serialize tag with quotes around attrs
                raise LookupError(
                    path, f"<{elem.tag} {' '.join('='.join(x) for x in elem.attrib.items())}>"
                ) from None
            return node.text or '' # TODO itertext()

        nodes = query_xml(tree, self.ad_path)
        return [
            Ad(
                urljoin(self.url, select(node, self.url_path)),
                (select(node, self.title_path) or '?').strip(),
                (select(node, self.location_path) or '?').strip(),
                # int((find_node(node, self.rooms_node).tail or '').strip() or '0'),
                self._fuzzy_float(select(node, self.rooms_path)),
                self.directory.now())
            for node in nodes]

    def _parse_json(self, data: bytes) -> list[Ad]:
        # TODO if this fails - validation error for encoding or not a dict
        result = cast(object, json.loads(data))
        assert isinstance(result, dict)

        @overload
        def lookup(data: dict[str, object], path: str, typ: type[_T]) -> _T:
            pass
        @overload
        def lookup(data: dict[str, object], path: str,
                   typ: tuple[type[_T], type[_U]]) -> _T | _U:
            pass
        def lookup(data: dict[str, object], path: str,
                   typ: type[_T] | tuple[type[_T], type[_U]]) -> _T | _U:
            try:
                return query_json(data, path, typ)[0]
            except IndexError:
                # TODO serialize data
                raise LookupError(path) from None

        # TODO type should be a list here, right?
        item_data = query_json(result, self.ad_path, dict)
        items = cast(list[dict[str, object]], item_data)

        #for item in item_data:
        #    if not isinstance(item, dict):
        #        raise LookupError(f'Bad element type {type(item).__name__} at {self.node}')
        #items = cast(list[dict[str, object]], item_data)
        ## TODO (its okay to parse from data: object because its internal method)
        #def parse_ad(data: object) -> None:
        #def extract_ad(data: object) -> None:
        #    pass

        # float, int, bool
        # None
        # {}, [] => [3, 'lol', True]

        return [
            Ad(
                urljoin(self.url, lookup(item, self.url_path, str)),
                lookup(item, self.title_path, str) or '?',
                lookup(item, self.location_path, str) or '?',
                # str(lookup(item, self.rooms_path, (str, int))),
                (self._fuzzy_float(x)
                 if isinstance(x := lookup(item, self.rooms_path, (str, int)), str) else x),
                self.directory.now())
            for item in items]

    @staticmethod
    def _fuzzy_float(value: str) -> float:
        match = re.search(r'\d+(\.\d+)?', value)
        #print('MATCHED', match and match[0], ' IN ', value)
        if not match:
            return 0
        return float(match[0])

    def query(self) -> list[Ad]:
        """TODO."""
        logger = getLogger(__name__)

        def _get_mtime(path: Path) -> datetime | None:
            try:
                # return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
                return datetime.fromtimestamp(path.stat().st_mtime)
            except FileNotFoundError:
                return None

        # TODO just remove ext here, think like: if we had a method get_cache, what would it return:
        # the path and the modified time, but not ext, because that can be extracted
        # or even better like get_mtime_fallback_to_multiple_files(file1, file2, ...):
        #cache_time = None
        #paths = (self.director.data_path / f'{self.host}.json', self.directory.data_path /
        # f'{self.host}.html')
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

        now = self.directory.now()
        if not mtime or now - mtime > timedelta(minutes=60):
            with cast(HTTPResponse, urlopen(self.url)) as response:
                data = response.read()

            ext = 'html'
            if response.getheader('Content-Type') == 'application/json':
                ext = 'json'

            path = self.directory.data_path / f'{self.host}.{ext}'
            with path.open('wb') as fw:
                fw.write(data)
            logger.debug('Fetched %s', self.url)

        with path.open('rb') as f:
            data = f.read()

        if ext == 'json':
            ads = self._parse_json(data)
        else:
            ads = self._parse_html(data)

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

        with self._ads_path.open('w', encoding='utf-8') as f:
            writer = csv.DictWriter(f, ['url', 'title', 'location', 'rooms', 'time'])
            writer.writeheader()
            for ad in ads:
                # row = [ad.url, ad.title, ad.location, ad.time.isoformat()]
                row = {'url': ad.url, 'title': ad.title, 'location': ad.location, 'rooms': ad.rooms,
                       'time': ad.time.isoformat()}
                writer.writerow(row)

        logger.info('Updated %d ad(s) from %s', len(ads), self.host)

    def get_ads(self) -> list[Ad]:
        """Get currently available flats of the company."""
        try:
            with self._ads_path.open(encoding='utf-8') as f:
                return [
                    Ad(row['url'], row['title'], row['location'], float(row['rooms']),
                       datetime.fromisoformat(row['time']))
                    for row in cast(Iterable[dict[str, str]], csv.DictReader(f))]
        except FileNotFoundError:
            return []

class Directory:
    """Directory of available flats from different real estate companies.

    .. attribute:: companies

       Source real estate companies.

    .. attribute:: title

       Title of the directory.

    .. attribute:: description

       Short description of the directory.

    .. attribute:: extra

       Any extra information about the directory as HTML.

    .. attribute:: data_directory

       Path to data directory.
    """

    def __init__(
        self, companies: Iterable[Company], *, title: str = 'Flat Directory',
        description: str = 'Currently available flats from {companies} real estate companies.',
        extra: str | None = None, data_path: PathLike[str] | str = 'data'
    ) -> None:
        self.companies = list(companies)
        self.title = title.strip()
        if not self.title:
            raise ValueError('Blank title')
        self.description = description.strip()
        if not self.description:
            raise ValueError('Blank description')
        self.extra = (extra.strip() or None) if extra else None
        self.data_path = Path(data_path)

        for company in companies:
            company.directory = self

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
            #except ValueError as e:
            #    logger.error('Bad HTML for %s (%s)', company.host, e.__cause__)
            # TODO check for JSON error
            except LookupError as e:
                logger.error('Failed to parse flat ad of %s (%s)', company.host, e)
            # make all paths valid OR check syntax in __init__
            #except SyntaxError as e:
            #    logger.error('Bad path for %s (%s)', company.host, e)

    def now(self) -> datetime:
        """TODO."""
        return datetime.now()

# request -> HTML
# parse -> [ads]
# update
# -
# read
# generate
