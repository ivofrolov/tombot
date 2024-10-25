import unittest

import tombot


class TestVariables(unittest.TestCase):
    def test_substitute(self):
        checks = (
            # escaped
            ("$$", {}, "$"),
            ("$$foo", {"foo": "bar"}, "$foo"),
            ("$$$foo", {"foo": "bar"}, "$bar"),
            # named
            ("$foo", {"foo": "bar"}, "bar"),
            ("$foo$baz", {"foo": "bar", "baz": "qux"}, "barqux"),
            ("$foo baz", {"foo": "bar"}, "bar baz"),
            ("$foo|baz", {"foo": "bar"}, "bar|baz"),
            # braced
            ("${foo}", {"foo": "bar"}, "bar"),
            ("${foo}${baz}", {"foo": "bar", "baz": "qux"}, "barqux"),
            ("${foo}$baz", {"foo": "bar", "baz": "qux"}, "barqux"),
            ("${foo|upper}", {"foo": "bar"}, "BAR"),
        )
        transformers = {"upper": str.upper}
        for string, variables, expected in checks:
            with self.subTest(string=string, variables=variables):
                self.assertEqual(
                    tombot.Variables(variables, transformers).substitute(string),
                    expected,
                )

    def test_substitute__invalid_template__raise_error(self):
        checks = (
            "$",
            "$ foo",
            "$1",
            "$1foo",
            "${",
            "${}",
            "${ foo}",
            "${foo }",
            "${1}",
            "${1foo}",
            "${$foo}",
        )
        for string in checks:
            with self.subTest(string=string):
                with self.assertRaises(ValueError):
                    tombot.Variables({}, {}).substitute(string)

    def test_substitute__unkown_variable__raise_error(self):
        checks = ("$foo", "${foo}")
        for string in checks:
            with self.subTest(string=string):
                with self.assertRaises(KeyError):
                    tombot.Variables({}, {}).substitute(string)

    def test_substitute__unkown_transformer__raise_error(self):
        checks = ("${foo|bar}",)
        for string in checks:
            with self.subTest(string=string):
                with self.assertRaises(KeyError):
                    tombot.Variables({}, {}).substitute(string)


class TestDefaultTransformers(unittest.TestCase):
    def test_to_kebab_case(self):
        checks = (
            ("Hello World", "hello-world"),
            ("hello_world", "hello-world"),
            ("hello-world", "hello-world"),
        )
        transform = tombot.DEFAULT_TRANSFORMERS["to_kebab_case"]
        for string, expected in checks:
            with self.subTest(string=string):
                self.assertEqual(transform(string), expected)

    def test_to_snake_case(self):
        checks = (
            ("Hello World", "hello_world"),
            ("hello-world", "hello_world"),
            ("hello_world", "hello_world"),
        )
        transform = tombot.DEFAULT_TRANSFORMERS["to_snake_case"]
        for string, expected in checks:
            with self.subTest(string=string):
                self.assertEqual(transform(string), expected)
