import re
import unittest

from appcomposer.utils import inject_absolute_urls

URL = 'http://foobar.com/foo/gadget.xml'

class UtilsTest(unittest.TestCase):
    def test_nomatch1(self):
        original = ""
        expected = ""
        self._test_injection(original, expected)

    def test_nomatch2(self):
        original = "<a href>"
        expected = "<a href>"
        self._test_injection(original, expected)

    def test_absolute_noquote_href(self):
        original = "<a href=http://go-lab-project.eu/>"
        expected = original
        self._test_injection(original, expected)

    def test_absolute_single_quote_href(self):
        original = "<a href='http://go-lab-project.eu/'>"
        expected = original
        self._test_injection(original, expected)

    def test_absolute_double_quote_href(self):
        original = """<a href="http://go-lab-project.eu/">"""
        expected = original
        self._test_injection(original, expected)

    def test_absolute_noquote_src(self):
        original = "<img src=http://go-lab-project.eu/>"
        expected = original
        self._test_injection(original, expected)

    def test_absolute_single_quote_src(self):
        original = "<img src='http://go-lab-project.eu/'>"
        expected = original
        self._test_injection(original, expected)

    def test_absolute_double_quote_src(self):
        original = """<img src="http://go-lab-project.eu/">"""
        expected = original
        self._test_injection(original, expected)

    def test_relative_noquote_href(self):
        original = "<a href=resource/>"
        expected = "<a href=http://foobar.com/foo/resource/>"
        self._test_injection(original, expected)

    def test_relative_single_quote_href(self):
        original = "<a href='resource/'>"
        expected = "<a href='http://foobar.com/foo/resource/'>"
        self._test_injection(original, expected)

    def test_relative_double_quote_href(self):
        original = """<a href="resource/">"""
        expected = """<a href="http://foobar.com/foo/resource/">"""
        self._test_injection(original, expected)

    def test_relative_noquote_src(self):
        original = "<img src=resource/>"
        expected = "<img src=http://foobar.com/foo/resource/>"
        self._test_injection(original, expected)

    def test_relative_single_quote_src(self):
        original = "<img src='resource/'>"
        expected = "<img src='http://foobar.com/foo/resource/'>"
        self._test_injection(original, expected)

    def test_relative_double_quote_src(self):
        original = """<img src="resource/">"""
        expected = """<img src="http://foobar.com/foo/resource/">"""
        self._test_injection(original, expected)

    def test_relative_double_quote_src_with_ng_include(self):
        original = """<img ng-include src="resource/">"""
        expected = """<img ng-include src="http://foobar.com/foo/resource/">"""
        self._test_injection(original, expected)

    def test_relative_double_quote_src_angular(self):
        original = """<ng-include src="resource/">"""
        expected = original
        self._test_injection(original, expected)

    def test_relative_double_quote_src_angular_with_word_in_middle(self):
        original = """<ng-doesnt exist src="resource/">"""
        expected = original
        self._test_injection(original, expected)

    def _test_injection(self, original, expected):
        obtained = inject_absolute_urls(original, URL)
        self.assertEquals(obtained, expected)

if __name__ == '__main__':
    unittest.main()
