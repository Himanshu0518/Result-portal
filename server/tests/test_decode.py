"""
Tests for app.importer.decode — file decoding and validation.
"""
from __future__ import annotations

import pytest

from app.importer.decode import decode_file, MAX_FILE_SIZE


class TestDecodeFile:

    # ── Happy paths ───────────────────────────────────────────────────────

    def test_valid_utf8(self):
        text, note = decode_file(b"hello,world\n", "data.csv")
        assert text == "hello,world\n"
        assert note is None

    def test_utf8_bom(self):
        bom_bytes = b"\xef\xbb\xbfhello,world\n"
        text, note = decode_file(bom_bytes, "data.csv")
        assert text == "hello,world\n"  # BOM stripped by utf-8-sig
        assert note is None

    def test_cp1252_fallback(self):
        # Bytes that are invalid UTF-8 but valid cp1252 (e.g. 0x80 = €)
        cp_bytes = b"price,\x80\n"
        text, note = decode_file(cp_bytes, "data.csv")
        assert note == "guessed cp1252"
        assert "price" in text

    def test_case_insensitive_extension(self):
        """'.CSV', '.Csv', etc. should be accepted."""
        text, note = decode_file(b"a,b\n1,2\n", "DATA.CSV")
        assert text == "a,b\n1,2\n"

    # ── Error paths ───────────────────────────────────────────────────────

    def test_empty_file(self):
        with pytest.raises(ValueError, match="empty"):
            decode_file(b"", "data.csv")

    def test_file_too_large(self):
        big = b"x" * (MAX_FILE_SIZE + 1)
        with pytest.raises(ValueError, match="10 MB"):
            decode_file(big, "data.csv")

    def test_binary_null_bytes(self):
        with pytest.raises(ValueError, match="binary"):
            decode_file(b"hello\x00world", "data.csv")

    def test_wrong_extension_txt(self):
        with pytest.raises(ValueError, match="Only .csv"):
            decode_file(b"content", "data.txt")

    def test_wrong_extension_xlsx(self):
        with pytest.raises(ValueError, match="Only .csv"):
            decode_file(b"content", "report.xlsx")

    def test_no_extension(self):
        with pytest.raises(ValueError, match="Only .csv"):
            decode_file(b"content", "noextension")
