# bot/tests/test_text_cleaner.py
"""
Tests per bot/utils/text_cleaner.py

Copre:
- clean_text() — None, stringa vuota, entità HTML, testo normale, caratteri speciali
"""

import pytest


class TestCleanText:

    def test_returns_empty_string_for_none(self):
        """None → stringa vuota."""
        from utils.text_cleaner import clean_text
        assert clean_text(None) == ""

    def test_returns_empty_string_for_empty_input(self):
        """Stringa vuota → stringa vuota."""
        from utils.text_cleaner import clean_text
        assert clean_text("") == ""

    def test_unescapes_html_entities(self):
        """Entità HTML classiche vengono decodificate."""
        from utils.text_cleaner import clean_text
        assert clean_text("R&amp;D") == "R&D"
        assert clean_text("&lt;script&gt;") == "<script>"
        assert clean_text("caf&eacute;") == "café"

    def test_returns_plain_text_unchanged(self):
        """Testo senza entità → invariato."""
        from utils.text_cleaner import clean_text
        assert clean_text("Hello, World!") == "Hello, World!"

    def test_handles_multiple_entities_in_one_string(self):
        """Più entità nella stessa stringa."""
        from utils.text_cleaner import clean_text
        result = clean_text("Tom &amp; Jerry &mdash; the best!")
        assert "&amp;" not in result
        assert "&" in result

    def test_handles_numeric_html_entities(self):
        """Entità numeriche HTML (&#xxx;)."""
        from utils.text_cleaner import clean_text
        assert clean_text("&#169;") == "©"
        assert clean_text("&#9829;") == "♥"
