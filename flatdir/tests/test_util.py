# TODO

from pathlib import Path
from unittest import TestCase
from tempfile import TemporaryDirectory
from typing import cast
from xml.etree import ElementTree
from importlib import resources

from flatdir.util import query_json, query_xml, copy_package

class TestCopyPackage(TestCase):
    # file -> _ / file : copy exists
    # dir -> _ / dir : dir exists, file inside exists

    # wrong time (dir-file or file-dir)
    # parent not existing
    # access
    # all os errors

    def setUp(self) -> None:
        self.dir = TemporaryDirectory()

    def tearDown(self) -> None:
        self.dir.cleanup()

    def test(self) -> None:
        path = Path(self.dir.name)
        copy_package(resources.files(f'{__package__}.res') / 'cats', path)
        self.assertEqual(list(path.iterdir()), [path / 'cat.txt', path / 'z']) # type: ignore[misc]
        self.assertEqual((path / 'cat.txt').read_text(), 'Meow!\n')

    def test_bad_dest_type(self) -> None:
        with self.assertRaises(IsADirectoryError):
            copy_package(resources.files(f'{__package__}.res') / 'cats' / 'cat.txt', self.dir.name)

class QueryJSONTest(TestCase):
    def setUp(self) -> None:
        self.cat: dict[str, object] = {'name': 'Happy', 'age': 7} #'fur': 'tabby'}
        self.cats: dict[str, object] = {
            'cats': [{'name': 'Happy', 'age': 7}, {'name': 'Grumpy', 'age': 13}]
        }

    def test(self) -> None:
        values = query_json(self.cat, 'name')
        self.assertEqual(values, ['Happy']) # type: ignore[misc]

    def test_object_members(self) -> None:
        values = query_json(self.cat, '*')
        self.assertEqual(values, ['Happy', 7]) # type: ignore[misc]

    def test_array_element(self) -> None:
        values = query_json(self.cats, 'cats.1')
        self.assertEqual(values, [cast(list[object], self.cats['cats'])[1]]) # type: ignore[misc]

    def test_array_elements(self) -> None:
        values = query_json(self.cats, 'cats.*')
        self.assertEqual(values, self.cats['cats'])

    def test_array_elements_member(self) -> None:
        values = query_json(self.cats, 'cats.*.name')
        self.assertEqual(values, ['Happy', 'Grumpy']) # type: ignore[misc]

    def test_missing(self) -> None:
        with self.assertRaisesRegex(LookupError, 'foo'):
            query_json(self.cats, 'cats.0.foo')

class QueryXMLTest(TestCase):
    def setUp(self) -> None:
        self.tree = ElementTree.fromstring(
            '<cats><cat name="Happy" />foo<cat name="Grumpy"></cat></cats>')

    def test(self) -> None:
        nodes = query_xml(self.tree, 'cat')
        self.assertEqual(nodes, self.tree[:])

    def test_attr(self) -> None:
        nodes = query_xml(self.tree, 'cat/@name')
        self.assertEqual(
            [ElementTree.tostring(node, encoding='unicode') for node in nodes], # type: ignore[misc]
            ['<name>Happy</name>', '<name>Grumpy</name>']) # type: ignore[misc]

    def test_tail(self) -> None:
        nodes = query_xml(self.tree, 'cat/tail()')
        self.assertEqual(
            [ElementTree.tostring(node, encoding='unicode') for node in nodes], # type: ignore[misc]
            ['<#text>foo</#text>']) # type: ignore[misc]
