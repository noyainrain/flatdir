# pylint: disable=missing-docstring

from datetime import datetime, timedelta
from http.server import HTTPServer, SimpleHTTPRequestHandler
from importlib import resources
import logging
from pathlib import Path
from socket import socket
from socketserver import BaseServer
from tempfile import TemporaryDirectory
from threading import Thread
from typing import ClassVar
import unittest
from urllib.parse import urljoin

from flatdir.directory import Ad, Company, Directory

class TestCase(unittest.TestCase):
    class _RequestHandler(SimpleHTTPRequestHandler):
        def __init__(self, request: tuple[bytes, socket], client_address: object,
                     server: BaseServer) -> None:
            super().__init__(request, client_address, server,
                             directory=str(resources.files(f'{__package__}.res')))

        def log_message(self, format: str, *args: object) -> None:
            # Disable logging
            # pylint: disable=redefined-builtin
            pass

    PORT = 16160

    _server: ClassVar[HTTPServer]

    @staticmethod
    def setUpClass() -> None:
        logging.disable()
        TestCase._server = HTTPServer(('localhost', TestCase.PORT), TestCase._RequestHandler)
        Thread(target=TestCase._server.serve_forever).start()

    @staticmethod
    def tearDownClass() -> None:
        TestCase._server.shutdown()
        TestCase._server.server_close()

    def setUp(self) -> None:
        # pylint: disable=consider-using-with
        self._dir = TemporaryDirectory()
        self.data_path = Path(self._dir.name)

    def tearDown(self) -> None:
        self._dir.cleanup()

    def expected_ads(self, company_url: str, time: datetime) -> list[Ad]:
        return [
            Ad(urljoin(company_url, 'mitte.html'), 'Luxurious Lodge', 'Mitte', 7, 2000, time),
            Ad(urljoin(company_url, 'kreuzberg.html'), 'Cozy Cottage', 'Kreuzberg', 1.5, 499.99,
               time)
        ]

    def assertEqual(self, first: object, second: object, msg: object = None) -> None:
        super().assertEqual(first, second, msg=msg)

class CompanyTest(TestCase):
    NOW = datetime(2023, 2, 3, 20)

    def test_update(self) -> None:
        company = Company(f'http://localhost:{self.PORT}/index.html', ".//li[@class='ad']",
                          'a/@href', 'a', 'span[1]:[^,]*', 'span[2]', 'span[3]')
        directory = Directory([company], data_path=self.data_path)
        directory.now = lambda: self.NOW # type: ignore[method-assign]

        company.update()
        ads = company.get_ads()
        self.assertEqual(ads, self.expected_ads(company.url, self.NOW))
        self.assertTrue(company.is_ok())

    def test_update_stored_ads(self) -> None:
        company = Company(f'http://localhost:{self.PORT}/index.html', ".//li[@class='ad']",
                          'a/@href', 'a', 'span[1]:[^,]*', 'span[2]', 'span[3]')
        directory = Directory([company], data_path=self.data_path)
        directory.now = lambda: self.NOW # type: ignore[method-assign]
        company.update()
        directory.now = lambda: self.NOW + timedelta(hours=1) # type: ignore[method-assign]

        company.update()
        ads = company.get_ads()
        self.assertEqual(ads, self.expected_ads(company.url, self.NOW))

    def test_query(self) -> None:
        company = Company(f'http://localhost:{self.PORT}/index.html', ".//li[@class='ad']",
                          'a/@href', 'a', 'span[1]:[^,]*', 'span[2]', 'span[3]')
        directory = Directory([company], data_path=self.data_path)
        directory.now = lambda: self.NOW # type: ignore[method-assign]

        ads = company.query()
        self.assertEqual(ads, self.expected_ads(company.url, self.NOW))

    def test_query_json(self) -> None:
        company = Company(f'http://localhost:{self.PORT}/ads.json', 'ads.*', 'url', 'title',
                          'location:[^,]*', 'rooms', 'rent')
        directory = Directory([company], data_path=self.data_path)
        directory.now = lambda: self.NOW # type: ignore[method-assign]

        ads = company.query()
        self.assertEqual(ads, self.expected_ads(company.url, self.NOW))

    def test_query_missing_element(self) -> None:
        directory = Directory(
            [Company(f'http://localhost:{self.PORT}/index.html', './/li', 'p', '', '', '', '')],
            data_path=self.data_path)
        company = directory.companies[0]
        with self.assertRaisesRegex(LookupError, 'p'):
            company.query()

    def test_query_communication_error(self) -> None:
        directory = Directory(
            [Company(f'http://localhost:{self.PORT}/foo', '', '', '', '', '', '')],
            data_path=self.data_path)
        company = directory.companies[0]
        with self.assertRaises(OSError):
            company.query()

class DirectoryTest(TestCase):
    def test_update(self) -> None:
        companies = [
            Company(f'http://happy.localhost:{self.PORT}/index.html', ".//li[@class='ad']",
                    'a/@href', 'a', 'span[1]:[^,]*', 'span[2]', 'span[3]'),
            Company(f'http://grumpy.localhost:{self.PORT}/ads.json', 'ads.*', 'url', 'title',
                    'location:[^,]*', 'rooms', 'rent'),
            Company(f'http://long.localhost:{self.PORT}/foo', '', '', '', '', '', '')
        ]
        directory = Directory(companies, data_path=self.data_path)
        directory.now = lambda: datetime(2023, 2, 3, 20) # type: ignore[method-assign]

        directory.update()
        ads = directory.get_ads()
        self.assertEqual(
            ads,
            [*self.expected_ads(companies[0].url, directory.now()),
             *self.expected_ads(companies[1].url, directory.now())])
