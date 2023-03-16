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

from flatdir.directory import Company, Directory

class CompanyTest(TestCase):
    URL = 'http://localhost:16080'

    server: ClassVar[HTTPServer]

    @staticmethod
    def _serve() -> None:
        CompanyTest.server.serve_forever()

    @staticmethod
    def setUpClass() -> None:
        handler = partial(SimpleHTTPRequestHandler,
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
        # self.data_path = Path('data')
        print('SET UP DATA PATH AT', self.data_path)
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
        #self.directory = Directory(self.companies.values(), data_path=self.data_path)

    def tearDownClass() -> None:
        CompanyTest.server.shutdown()

    # TODO
    def test_update(self) -> None:
        pass
        # update()
        # ads = get_ads()
        # assertEqual(ads, [...])

    def test_update(self) -> None:
        pass

    #def test_get_ads(self) -> None:
    #    pass

    PATHS = ('.//li', 'a', 'a', "span[@class='location']", "span[@class='rooms']")

    def test_query(self) -> None:
        # list[Ad]
        #company = Company(urljoin(self.URL, 'index.html'), *self.PATHS)
        #_ = Directory([company], data_path=self.data_path)
        #ads = company.query()
        #ads = self.companies['html'].query()

        directory = Directory([Company(urljoin(self.URL, 'index.html'), *self.PATHS)],
                              data_path=self.data_path)
        ads = directory.companies[0].query()
        self.assertEqual(len(ads), 2)
        self.assertEqual(ads[0].url, urljoin(self.URL, 'foobar.html'))
        self.assertEqual(ads[0].title, 'Foobar')
        self.assertEqual(ads[0].location, 'Kreuzberg')
        self.assertEqual(ads[0].rooms, '4')
        self.assertAlmostEqual(ads[0].time, datetime.now(timezone.utc), delta=timedelta(seconds=1))
        self.assertEqual(ads[1].url, urljoin(self.URL, 'oink.html'))
        self.assertAlmostEqual(ads[1].time, datetime.now(timezone.utc), delta=timedelta(seconds=1))

    def test_query_json(self) -> None:
        # TODO path should be flats.*
        # NOTE for future use: url_pattern=foobar.com/flats/{}.html

        company = Company(urljoin(self.URL, 'ads.json'), 'flats', 'url', 'title', 'location',
                         'rooms')
        _ = Directory([company], data_path=self.data_path)

        ads = company.query()
        #ads = self.companies['json'].query()
        self.assertEqual(len(ads), 2)
        self.assertEqual(ads[0].url, urljoin(self.URL, 'foobar.html'))
        self.assertEqual(ads[1].url, urljoin(self.URL, 'oink.html'))
        self.assertEqual(ads[1].title, 'Oink')
        self.assertEqual(ads[1].location, 'Mitte')
        self.assertEqual(ads[1].rooms, '2')

    def test_query_network_error(self) -> None:
        # broker = Broker('http://example.invalid', '', '', '', '', '')

        company = Company('http://localhost:16080/doesnotexist', *self.PATHS)
        _ = Directory([company], data_path=self.data_path)

        with self.assertRaises(OSError):
            company.query()
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

        company = Company(urljoin(self.URL, 'index.html'), './/li', 'a', 'p',
                          "span[@class='location']", "span[@class='rooms']")
        _ = Directory([company], data_path=self.data_path)

        # with assertRaisesRegex(LookupError):
        with self.assertRaises(LookupError):
            company.query()
            # self.companies['typo'].query()

    # TODO if we parse rooms as number (or generally parse nonstring fields) -> check for parsing
    # errors here
