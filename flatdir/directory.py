"""Flat ad directory logic."""

from __future__ import annotations

import csv
from collections.abc import Iterable
import dataclasses
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
from json import JSONDecodeError
from locale import atof, localeconv
from logging import getLogger
from os import PathLike
from pathlib import Path
import re
from typing import ClassVar, cast
from urllib.error import URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import urlopen
from urllib.response import addinfourl
from xml.etree import ElementTree
from xml.etree.ElementTree import Element

import html5lib

from .util import query_json, query_xml

@dataclass
class Ad:
    """Flat advertisement.

    .. attribute:: url

       URL of the ad.

    .. attribute:: host

       Hostname of the related real estate company.

    .. attribute:: title

       Title of the ad.

    .. attribute:: location

       Location of the flat.

    .. attribute:: rooms

       Number of rooms of the flat.

    .. attribute:: rent

       TODO.

    .. attribute:: time

       Publication time.
    """

    url: str
    title: str
    location: str
    rooms: float
    rent: float
    time: datetime

    def __post_init__(self) -> None:
        self.host = urlsplit(self.url).hostname
        if not self.host:
            raise ValueError(f'Bad url {self.url}')
        self.title = self.title.strip()
        if not self.title:
            raise ValueError('Blank title')
        self.location = self.location.strip()
        if not self.location:
            raise ValueError('Blank location')

class Company:
    """Real estate company.

    .. attribute:: url

       URL of the document containing currently available flats of the company.

    .. attribute:: host

       Hostname of the company.

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

    .. attribute:: rent_path

       TODO.

    .. attribute:: location_filter

       Term that the location of a flat needs to contain to be included.

    .. attribute:: TIMEOUT

       Time since the last successful update after which the company is considered unavailable.
    """

    TIMEOUT: ClassVar[timedelta] = timedelta(hours=1, minutes=30)

    _CACHE_TTL: ClassVar[timedelta] = timedelta(minutes=30)

    def __init__(self, url: str, ad_path: str, url_path: str, title_path: str, location_path: str,
                 rooms_path: str, rent_path: str, *, location_filter: str = '') -> None:
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
        self.rent_path = rent_path
        self.location_filter = location_filter

        self._directory: Directory | None = None
        self._ads_path = Path()

    @property
    def directory(self) -> Directory:
        """Related flat ad directory."""
        if not self._directory:
            raise ValueError('Unset directory')
        return self._directory

    @directory.setter
    def directory(self, value: Directory) -> None:
        if self._directory:
            raise ValueError('Already set directory')
        self._directory = value
        self._ads_path = self._directory.data_path / f'{self.host}.csv'

    def is_ok(self) -> bool:
        """Indicate if the company is available at the moment."""
        try:
            return (self.directory.now() - datetime.fromtimestamp(self._ads_path.stat().st_mtime)
                    < Company.TIMEOUT)
        except FileNotFoundError:
            return False

    def get_ads(self) -> list[Ad]:
        """Get currently available flats."""
        try:
            with self._ads_path.open(encoding='utf-8') as f:
                return [
                    Ad(row['url'], row['title'], row['location'], float(row['rooms']),
                       # Update on read :)
                       float(row.get('rent', '0')),
                       datetime.fromisoformat(row['time']))
                    for row in cast(Iterable[dict[str, str]], csv.DictReader(f))]
        except FileNotFoundError:
            return []

    def update(self) -> list[Ad]:
        """Update current ads."""
        old_ads = {ad.url: ad for ad in self.get_ads()}
        ads = [dataclasses.replace(ad, time=old_ads.get(ad.url, ad).time) for ad in self.query()]

        with self._ads_path.open('w', encoding='utf-8') as f:
            writer = csv.DictWriter(f, ['url', 'title', 'location', 'rooms', 'rent', 'time'])
            writer.writeheader()
            for ad in ads:
                row = {'url': ad.url, 'title': ad.title, 'location': ad.location, 'rooms': ad.rooms,
                       'rent': ad.rent, 'time': ad.time.isoformat()}
                writer.writerow(row)

        return ads

    def query(self) -> list[Ad]:
        """Query current ads.

        If there is a problem communicating with the company, a :exc:`urllib.error.URLError` is
        raised. If there is a problem parsing the ads, a :exc:`LookupError` or :exc:`ValueError` is
        raised.
        """
        paths = [self.directory.data_path / f'{self.host}.html',
                 self.directory.data_path / f'{self.host}.json']
        for path in paths:
            try:
                cache_time = datetime.fromtimestamp(path.stat().st_mtime)
                break
            except FileNotFoundError:
                pass
        else:
            cache_time = None

        if not cache_time or self.directory.now() - cache_time > self._CACHE_TTL:
            with cast(addinfourl, urlopen(self.url)) as response:
                content_type = response.headers.get_content_type()
                data = response.read()
            try:
                ext = {'text/html': '.html', 'application/json': '.json'}[content_type]
            except KeyError:
                raise ValueError(f'Unknown document type {content_type}') from None
            path = self.directory.data_path / f'{self.host}{ext}'
            path.write_bytes(data)
            getLogger(__name__).debug('Fetched %s', self.url)

        parse = {'.html': self._parse_html, '.json': self._parse_json}[path.suffix]
        ads = parse(path.read_bytes())
        if self.location_filter:
            ads = [ad for ad in ads if self.location_filter in ad.location]
        ads = [ad for ad in ads if ad.rooms]
        return ads

    def _parse_html(self, data: bytes) -> list[Ad]:
        def query(element: Element, path: str) -> str:
            try:
                element = query_xml(element, path)[0]
            except IndexError:
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
                self._fuzzy_float(query(element, self.rooms_path)),
                self._fuzzy_float(query(element, self.rent_path)), self.directory.now())
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
                self._fuzzy_float(query_json(value, self.rent_path, (str, int, float))[0]),
                self.directory.now())
            for value in values]

    @staticmethod
    def _fuzzy_float(value: str | int | float) -> float:
        if isinstance(value, (int, float)):
            return float(value)
        conv = cast(dict[str, str], localeconv())
        decimal, grouping = re.escape(conv['decimal_point']), re.escape(conv['thousands_sep'])
        match = re.search(rf'[\d{grouping}]+({decimal}\d+)?', value)
        return atof(match[0]) if match else .0

class Directory:
    """Directory of available flats from different real estate companies.

       Numbers are parsed according to the current locale.

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
        self.title = title.strip()
        if not self.title:
            raise ValueError('Blank title')
        self.description = description.strip()
        if not self.description:
            raise ValueError('Blank description')
        self.extra = (extra.strip() or None) if extra else None
        self.data_path = Path(data_path)

        self.companies = list(companies)
        for company in self.companies:
            company.directory = self

    def get_ads(self) -> list[Ad]:
        """Get currently available flats."""
        return [ad for company in self.companies for ad in company.get_ads()]

    def update(self) -> None:
        """Aggregate current ads from all :attr:`companies`."""
        logger = getLogger(__name__)
        for company in self.companies:
            try:
                ads = company.update()
                logger.info('Updated %d ad(s) from %s', len(ads), company.host)
            except URLError as e:
                logger.error('Failed to communicate with %s (%s)', company.host, e.reason)
            except (LookupError, ValueError, SyntaxError) as e:
                logger.error('Failed to parse flat ads from %s (%s)', company.host, e)

    def now(self) -> datetime:
        """Return the current local date and time."""
        return datetime.now()
