# TODO

# pylint: disable=missing-docstring

from collections.abc import Callable
from datetime import datetime, timedelta
from http.server import HTTPServer, SimpleHTTPRequestHandler
import logging
from threading import Thread
from tempfile import TemporaryDirectory
from typing import ClassVar
from pathlib import Path
from functools import partial
from importlib import resources
from unittest import TestCase
from urllib.parse import urljoin

from flatdir.directory import Ad, Company, Directory

class HTTPRequestHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        # pylint: disable=redefined-builtin
        pass

# fixed_time / NOW / ADS -> see how it works in combitionation with DirectoryTest.test_update
def fixed_time(time: datetime) -> Callable[[], datetime]:
    def f() -> datetime:
        return time
    return f

class BaseTestCase(TestCase):
    URL = 'http://localhost:16080'

    server: ClassVar[HTTPServer]

    @staticmethod
    def setUpClass() -> None:
        logging.disable()
        handler = partial(HTTPRequestHandler, #SimpleHTTPRequestHandler,
                          directory=resources.path('flatdir.tests.res', '.'))
        BaseTestCase.server = HTTPServer(('', 16080), handler)
        def serve() -> None:
            BaseTestCase.server.serve_forever()
        thread = Thread(target=serve)
        thread.start()

    @staticmethod
    def tearDownClass() -> None:
        BaseTestCase.server.shutdown()
        BaseTestCase.server.server_close()
        #from time import sleep
        #sleep(1)
        # BaseTestCase.server = None

    def setUp(self) -> None:
        # d = mkdtemp(prefix='flatdir-')
        # pylint: disable=consider-using-with
        self._dir = TemporaryDirectory()
        self.data_path = Path(self._dir.name)
        #print('SET UP DATA PATH AT', self.data_path)

    def tearDown(self) -> None:
        self._dir.cleanup()

    def get_expected_ads(self, url: str, time: datetime) -> list[Ad]:
        return [
            Ad(urljoin(url, 'foobar.html'), 'Foobar', 'Kreuzberg', 4, time),
            Ad(urljoin(url, 'oink.html'), 'Oink', 'Mitte', 2.5, time)
        ]

class CompanyTest(BaseTestCase):
    NOW = datetime(2023, 3, 16, 14)
    ADS = [
        Ad(urljoin(BaseTestCase.URL, 'foobar.html'), 'Foobar', 'Kreuzberg', 4, NOW),
        Ad(urljoin(BaseTestCase.URL, 'oink.html'), 'Oink', 'Mitte', 2.5, NOW)
    ]

    def setUp(self) -> None:
        super().setUp()
        self.directory = Directory([Company(urljoin(self.URL, 'index.html'), *self.PATHS)],
                                   data_path=self.data_path)

    def test_update(self) -> None:
        #print('COMPANY NOW', CompanyTest.NOW, CompanyTest.NOW.tzinfo)
        self.directory.now = fixed_time(CompanyTest.NOW) # type: ignore[method-assign]
        company = self.directory.companies[0]
        company.update()
        ads = company.get_ads()
        #print('LOADTIME', ads[0].time, ads[0].time.tzinfo)
        self.assertEqual(ads, CompanyTest.ADS)
        self.assertTrue(company.is_ok())
        #self.assertTrue(False)

    def test_update_again(self) -> None:
        company = self.directory.companies[0]
        self.directory.now = fixed_time(CompanyTest.NOW) # type: ignore[method-assign]
        company.update()
        self.directory.now = fixed_time( # type: ignore[method-assign]
            CompanyTest.NOW + timedelta(hours = 5))
        company.update()
        ads = company.get_ads()
        self.assertEqual(ads, CompanyTest.ADS)

    PATHS = ('.//li', 'a/@href', 'a', "span[@class='location']", "span[@class='rooms']")

    def test_query(self) -> None:
        directory = Directory([Company(urljoin(self.URL, 'index.html'), *self.PATHS)],
                              data_path=self.data_path)
        directory.now = fixed_time(CompanyTest.NOW) # type: ignore[method-assign]
        ads = directory.companies[0].query()
        self.assertEqual(ads, CompanyTest.ADS)

        # list[Ad]
        #company = Company(urljoin(self.URL, 'index.html'), *self.PATHS)
        #_ = Directory([company], data_path=self.data_path)
        #ads = company.query()
        #ads = self.companies['html'].query()

    def test_query_json(self) -> None:
        # NOTE for future use: url_pattern=foobar.com/flats/{}.html
        company = Company(urljoin(self.URL, 'ads.json'), 'flats.*', 'url', 'title', 'location',
                          'rooms')
        directory = Directory([company], data_path=self.data_path)
        directory.now = fixed_time(CompanyTest.NOW) # type: ignore[method-assign]

        ads = directory.companies[0].query()
        self.assertEqual(ads, CompanyTest.ADS)

    def test_query_network_error(self) -> None:
        # broker = Broker('http://example.invalid', '', '', '', '', '')

        company = Company('http://localhost:16080/doesnotexist', *self.PATHS)
        directory = Directory([company], data_path=self.data_path)

        with self.assertRaises(OSError):
            directory.companies[0].query()
            # self.companies['broken'].query()

    #def test_query_content_error(self) -> None:
    #    broker = Broker('http://localhost:16080/blob', *self.PATHS)
    #    with self.assertRaisesRegex(ValueError, 'HTML'):
    #        broker.query()

    def test_query_config_error(self) -> None:
        # TypeError: 'NoneType' object is not callable

        company = Company(urljoin(self.URL, 'index.html'), './/li', 'a/@href', 'p',
                          "span[@class='location']", "span[@class='rooms']")
        directory = Directory([company], data_path=self.data_path)

        # with assertRaisesRegex(LookupError):
        with self.assertRaises(LookupError):
            directory.companies[0].query()
            # self.companies['typo'].query()

class DirectoryTest(BaseTestCase):
    def test_update(self) -> None:
        companies = [
            Company('http://a.localhost:16080/index.html', './/li', 'a/@href', 'a', 'span[1]',
                    'span[2]'),
            Company('http://b.localhost:16080/ads.json', 'flats.*', 'url', 'title', 'location',
                    'rooms'),
            Company('http://c.localhost:16080/404', '', '', '', '', '')
        ]
        directory = Directory(companies, data_path=self.data_path)
        directory.now = fixed_time(datetime(2023, 3, 16, 14)) # type: ignore[method-assign]

        directory.update()
        ads = directory.get_ads()
        expected_ads = [*self.get_expected_ads('http://a.localhost:16080', directory.now()),
                        *self.get_expected_ads('http://b.localhost:16080', directory.now())]
        self.assertEqual(ads, expected_ads)
