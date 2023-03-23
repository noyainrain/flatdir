# TODO

from unittest import TestCase
from typing import cast

from flatdir.util import query_json

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
