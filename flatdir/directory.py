"""Flat ad directory logic."""

from __future__ import annotations

import csv
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta
from http.client import HTTPResponse
import json
from json import JSONDecodeError
from logging import getLogger
from os import PathLike
from pathlib import Path
import re
from typing import ClassVar, cast
from urllib.parse import urljoin, urlsplit
from urllib.request import urlopen
from xml.etree import ElementTree
from xml.etree.ElementTree import Element

import html5lib

from .util import query_json, query_xml

# CONTINUE REVIEW

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

    .. attribute:: rooms_optional

       Ignore entries, that don't have a room count entry.

    .. attribute:: location_filter

       Term that the location of a flat needs to contain to be included.

    .. attribute:: TIMEOUT

       Time since the last successful update after which the company is considered unavailable.
    """

    TIMEOUT: ClassVar[timedelta] = timedelta(hours=1, minutes=30)

    def __init__(self, url: str, ad_path: str, url_path: str, title_path: str, location_path: str,
                 rooms_path: str, *, rooms_optional: bool = False, location_filter: str = '') -> None:
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
        self.rooms_optional = rooms_optional
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
                    < Company.TIMEOUT)
        except FileNotFoundError:
            return False

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

    # REVIEWED
    def _parse_html(self, data: bytes) -> list[Ad]:
        def query(element: Element, path: str, optional: bool = False) -> str:
            try:
                element = query_xml(element, path)[0]
            except IndexError:
                if optional:
                    return ''
                else:
                    xml = ElementTree.tostring(Element(element.tag, attrib=element.attrib),
                                               encoding='unicode')
                    raise LookupError(f'No {path} in {xml}') from None
            return ''.join(element.itertext())

        # Unfortunately strict parsing fails for most real-world companies
        tree = html5lib.parse(data, namespaceHTMLElements=False)
        elements = query_xml(tree, self.ad_path)
        return [
            Ad(
                urljoin(self.url, query(element, self.url_path)),
                query(element, self.title_path).strip() or '?',
                query(element, self.location_path).strip() or '?',
                self._fuzzy_float(query(element, self.rooms_path, self.rooms_optional)), self.directory.now())
            for element in elements]

    def _parse_json(self, data: bytes) -> list[Ad]:
        try:
            root = cast(object, json.loads(data))
        except JSONDecodeError as e:
            raise ValueError(f'Bad document line {e.lineno}') from e
        if not isinstance(root, dict):
            raise ValueError(f'Bad document root type {type(root).__name__}')

        values = cast(list[dict[str, object]], query_json(root, self.ad_path, dict))
        return [
            Ad(
                urljoin(self.url, query_json(value, self.url_path, str)[0]),
                query_json(value, self.title_path, str)[0].strip() or '?',
                query_json(value, self.location_path, str)[0].strip() or '?',
                self._fuzzy_float(query_json(value, self.rooms_path, (str, int, float))[0]),
                self.directory.now())
            for value in values]

    @staticmethod
    def _fuzzy_float(value: str | int | float) -> float:
        if isinstance(value, str):
            match = re.search(r'\d+(\.\d+)?', value)
            value = match[0] if match else 0
        return float(value)
    # /REVIEWED

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
            except (ValueError, LookupError) as e:
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
