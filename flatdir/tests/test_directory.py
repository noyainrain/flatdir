from unittest import TestCase
from datetime import datetime, timedelta, timezone
from http.server import HTTPServer, SimpleHTTPRequestHandler
from threading import Thread
from tempfile import TemporaryDirectory, mkdtemp
from typing import ClassVar
from pathlib import Path
from functools import partial
from importlib import resources
from urllib.parse import urljoin

from flatdir.directory import Ad, Company, Directory

from collections.abc import Callable

class HTTPRequestHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        pass

# fixed_time / NOW / ADS -> see how it works in combitionation with DirectoryTest.test_update
def fixed_time(time: datetime) -> Callable[[], datetime]:
    def f() -> datetime:
        return time
    return f

class CompanyTest(TestCase):
    URL = 'http://localhost:16080'
    NOW = datetime(2023, 3, 16, 14)
    ADS = [
        Ad(urljoin(URL, 'foobar.html'), 'Foobar', 'Kreuzberg', '4', NOW),
        Ad(urljoin(URL, 'oink.html'), 'Oink', 'Mitte', '2', NOW)
    ]

    server: ClassVar[HTTPServer]

    @staticmethod
    def _serve() -> None:
        CompanyTest.server.serve_forever()

    @staticmethod
    def setUpClass() -> None:
        handler = partial(HTTPRequestHandler, #SimpleHTTPRequestHandler,
                          directory=resources.path('flatdir.tests.res', '.'))
        CompanyTest.server = HTTPServer(('', 16080), handler)
        thread = Thread(target=CompanyTest._serve)
        thread.start()
        #with socketserver.TCPServer(("", PORT), Handler) as httpd:
        #    print("serving at port", PORT)
        #    httpd.serve_forever()

    def setUp(self) -> None:
        #d = TemporaryDirectory()
        #self.data_path = Path(d.name)

        # TODO remove tempdir after (use TemporaryDirectory.cleanup())
        d = mkdtemp(prefix='flatdir-')
        self.data_path = Path(d)
        #print('SET UP DATA PATH AT', self.data_path)

        # self.data_path = Path('data')
        #self.data_path.mkdir(exist_ok=True)
        #for path in ['localhost.html', 'localhost.json']:
        #    (self.data_path / path).unlink(missing_ok=True)

        #self.companies = {
        #    'html': Company(urljoin(self.URL, 'index.html'), *self.PATHS),
        #    'json': Company(urljoin(self.URL, 'ads.json'), 'flats', 'url', 'title', 'location',
        #                    'rooms'),
        #    'broken': Company('http://localhost:16080/doesnotexist', *self.PATHS),
        #    'typo': Company(urljoin(self.URL, 'index.html'), './/li', 'a', 'p',
        #                    "span[@class='location']", "span[@class='rooms']")
        #}

        self.directory = Directory([Company(urljoin(self.URL, 'index.html'), *self.PATHS)],
                                   data_path=self.data_path)

    @staticmethod
    def tearDownClass() -> None:
        CompanyTest.server.shutdown()

    def test_update(self) -> None:
        #print('COMPANY NOW', CompanyTest.NOW, CompanyTest.NOW.tzinfo)
        self.directory.now = fixed_time(CompanyTest.NOW) # type: ignore[assignment]
        company = self.directory.companies[0]
        company.update()
        ads = company.get_ads()
        #print('LOADTIME', ads[0].time, ads[0].time.tzinfo)
        self.assertEqual(ads, CompanyTest.ADS)
        self.assertTrue(company.is_ok())
        #self.assertTrue(False)

    def test_update_again(self) -> None:
        company = self.directory.companies[0]
        self.directory.now = fixed_time(CompanyTest.NOW) # type: ignore[assignment]
        company.update()
        self.directory.now = fixed_time(CompanyTest.NOW + timedelta(hours = 5)) # type: ignore[assignment]
        company.update()
        ads = company.get_ads()
        self.assertEqual(ads, CompanyTest.ADS)
        self.assertTrue(False)

    PATHS = ('.//li', 'a/@href', 'a', "span[@class='location']", "span[@class='rooms']")

    def test_query(self) -> None:
        directory = Directory([Company(urljoin(self.URL, 'index.html'), *self.PATHS)],
                              data_path=self.data_path)
        directory.now = fixed_time(CompanyTest.NOW) # type: ignore[assignment]
        ads = directory.companies[0].query()
        self.assertEqual(ads, CompanyTest.ADS)

        # list[Ad]
        #company = Company(urljoin(self.URL, 'index.html'), *self.PATHS)
        #_ = Directory([company], data_path=self.data_path)
        #ads = company.query()
        #ads = self.companies['html'].query()

        #self.assertEqual(len(ads), 2)
        #self.assertEqual(ads[0].url, urljoin(self.URL, 'foobar.html'))
        #self.assertEqual(ads[0].title, 'Foobar')
        #self.assertEqual(ads[0].location, 'Kreuzberg')
        #self.assertEqual(ads[0].rooms, '4')
        ## TODO self.assertAlmostEqual(ads[0].time, datetime.now(timezone.utc), delta=timedelta(seconds=1))
        #self.assertEqual(ads[1].url, urljoin(self.URL, 'oink.html'))
        ## TODO self.assertAlmostEqual(ads[1].time, datetime.now(timezone.utc), delta=timedelta(seconds=1))

    def test_query_json(self) -> None:
        # NOTE for future use: url_pattern=foobar.com/flats/{}.html

        company = Company(urljoin(self.URL, 'ads.json'), 'flats.*', 'url', 'title', 'location',
                         'rooms')
        directory = Directory([company], data_path=self.data_path)
        directory.now = fixed_time(CompanyTest.NOW) # type: ignore[assignment]

        ads = directory.companies[0].query()
        self.assertEqual(ads, CompanyTest.ADS)

        #ads = self.companies['json'].query()
        #self.assertEqual(len(ads), 2)
        #self.assertEqual(ads[0].url, urljoin(self.URL, 'foobar.html'))
        #self.assertEqual(ads[1].url, urljoin(self.URL, 'oink.html'))
        #self.assertEqual(ads[1].title, 'Oink')
        #self.assertEqual(ads[1].location, 'Mitte')
        #self.assertEqual(ads[1].rooms, '2')

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
        # TODO make a note about SyntaxError, it will be raised on query() if there is a syntaxerror
        # in the xpath. it would be nice if it would be raised on Company() init
        # XXX bug in the std library for nonmatching brackets [ ]
        # TypeError: 'NoneType' object is not callable

        company = Company(urljoin(self.URL, 'index.html'), './/li', 'a/@href', 'p',
                          "span[@class='location']", "span[@class='rooms']")
        directory = Directory([company], data_path=self.data_path)

        # with assertRaisesRegex(LookupError):
        with self.assertRaises(LookupError):
            directory.companies[0].query()
            # self.companies['typo'].query()

    # TODO if we parse rooms as number (or generally parse nonstring fields) -> check for parsing
    # errors here
