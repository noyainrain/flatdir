# pylint: disable=missing-docstring

from importlib import resources
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from xml.etree import ElementTree

from flatdir.util import copy_resource, query_json, query_xml

class CopyResourceTest(TestCase):
    def setUp(self) -> None:
        # pylint: disable=consider-using-with
        self.dir = TemporaryDirectory()

    def tearDown(self) -> None:
        self.dir.cleanup()

    def test(self) -> None:
        dst = Path(self.dir.name)
        copy_resource(resources.files(f'{__package__}.res') / 'cats', dst)
        self.assertEqual(list(dst.iterdir()), # type: ignore[misc]
                         [dst / 'happy.txt', dst / 'clowder']) # type: ignore[misc]
        self.assertEqual((dst / 'happy.txt').read_text(), 'Meow!\n')

    def test_inaccessible_dst(self) -> None:
        with self.assertRaises(IsADirectoryError):
            copy_resource(resources.files(f'{__package__}.res') / 'cats' / 'happy.txt',
                          self.dir.name)

class QueryJSONTest(TestCase):
    def setUp(self) -> None:
        self.cats = [{'name': 'Happy', 'lives': 9}, {'name': 'Grumpy', 'lives': 7}]

    def test(self) -> None:
        values = query_json(self.cats, '1.name', str)
        self.assertEqual(values, ['Grumpy']) # type: ignore[misc]

    def test_object_wildcard(self) -> None:
        values = query_json(self.cats, '0.*')
        self.assertEqual(values, ['Happy', 9]) # type: ignore[misc]

    def test_array_wildcard(self) -> None:
        values = query_json(self.cats, '*.lives')
        self.assertEqual(values, [9, 7]) # type: ignore[misc]

    def test_missing_item(self) -> None:
        with self.assertRaisesRegex(LookupError, 'foo'):
            query_json(self.cats, '1.name.foo')

    def test_bad_item_type(self) -> None:
        with self.assertRaisesRegex(ValueError, 'item'):
            query_json(self.cats, '1.name', int)

class QueryXMLTest(TestCase):
    def setUp(self) -> None:
        self.tree = ElementTree.fromstring(
            '<cats><cat name="Happy" />Meow!<cat name="Grumpy"></cat></cats>')

    def test(self) -> None:
        elements = query_xml(self.tree, 'cat')
        self.assertEqual(elements, self.tree[:])

    def test_attribute(self) -> None:
        elements = query_xml(self.tree, 'cat/@name')
        self.assertEqual(
            [ElementTree.tostring(element, encoding='unicode')
             for element in elements], # type: ignore[misc]
            ['<name>Happy</name>', '<name>Grumpy</name>']) # type: ignore[misc]

    def test_tail(self) -> None:
        elements = query_xml(self.tree, 'cat/tail()')
        self.assertEqual(
            [ElementTree.tostring(element, encoding='unicode')
             for element in elements], # type: ignore[misc]
            ['<#text>Meow!</#text>']) # type: ignore[misc]
