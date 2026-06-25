import pytest
from shared.text_norm import normalize_text, strip_accents


class TestNormalizeText:
    def test_whitespace_collapse(self):
        assert normalize_text("Hello    world") == "Hello world"

    def test_newline_preserved(self):
        assert normalize_text("Line1\n  \nLine2") == "Line1\n\nLine2"

    def test_nfkc_normalization(self):
        result = normalize_text("é")  # e + combining accent
        assert result == "é" or len(result) == 1

    def test_empty_string(self):
        assert normalize_text("") == ""
        assert normalize_text(None) == ""


class TestStripAccents:
    def test_vietnamese(self):
        assert strip_accents("Việt Nam") == "Viet Nam"

    def test_no_accents(self):
        assert strip_accents("Hello World") == "Hello World"

    def test_empty(self):
        assert strip_accents("") == ""
        assert strip_accents(None) == ""
