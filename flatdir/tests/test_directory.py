from unittest import TestCase
from datetime import datetime, timedelta, timezone
from http.server import HTTPServer, SimpleHTTPRequestHandler
from threading import Thread
from typing import ClassVar
from pathlib import Path
from functools import partial
from importlib import resources
from urllib.parse import urljoin

from flatdir.directory import Broker

class CompanyTest(TestCase):
    #def test_get_ads(self) -> None:
    #    pass

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
        data_path = Path('data')
        data_path.mkdir(exist_ok=True)
        (data_path / 'localhost.html').unlink(missing_ok=True)

    def tearDownClass() -> None:
        CompanyTest.server.shutdown()

    #def test_update(self) -> None:
    #    pass

    PATHS = ('.//li', 'a', 'a', "span[@class='location']", "span[@class='rooms']")

    def test_query(self) -> None:
        # list[Ad]
        broker = Broker(urljoin(self.URL, 'index.html'), *self.PATHS)
        ads = broker.query()
        self.assertEqual(len(ads), 2)
        self.assertEqual(ads[0].url, urljoin(self.URL, 'foobar.html'))
        self.assertEqual(ads[0].title, 'Foobar')
        self.assertEqual(ads[0].location, 'Kreuzberg')
        self.assertEqual(ads[0].rooms, '4')
        self.assertAlmostEqual(ads[0].time, datetime.now(timezone.utc), delta=timedelta(seconds=1))
        self.assertEqual(ads[1].url, urljoin(self.URL, 'oink.html'))
        self.assertEqual(ads[1].title, 'Oink')
        self.assertEqual(ads[1].location, 'Mitte')
        self.assertEqual(ads[1].rooms, '2')
        self.assertAlmostEqual(ads[1].time, datetime.now(timezone.utc), delta=timedelta(seconds=1))

        # error: content error HTML parsing errors?
        # error: config error (path to HTML elements missing or something...)

    def test_query_network_error(self) -> None:
        # broker = Broker('http://example.invalid', '', '', '', '', '')
        broker = Broker('http://localhost:16080/doesnotexist', *self.PATHS)
        with self.assertRaises(OSError):
            broker.query()

    def test_query_content_error(self) -> None:
        broker = Broker('http://localhost:16080/blob', *self.PATHS)
        with self.assertRaisesRegex(ValueError, 'HTML'):
            broker.query()

    def test_query_config_error(self) -> None:
        # TODO make a note about SyntaxError, it will be raised on query() if there is a syntaxerror
        # in the xpath. it would be nice if it would be raised on Company() init
        # XXX bug in the std library for nonmatching brackets [ ]
        # TypeError: 'NoneType' object is not callable
        broker = Broker(urljoin(self.URL, 'index.html'), './/li', 'a', 'p',
                        "span[@class='location']", "span[@class='rooms']")
        # with assertRaisesRegex(LookupError):
        with self.assertRaises(LookupError):
            broker.query()

    # TODO if we parse rooms as number (or generally parse nonstring fields) -> check for parsing
    # errors here
