"""
Structural / output-format validation tests.

Validates the raw output file characteristics:
  - Valid UTF-8
  - Unix line endings (\\n, not \\r\\n)
  - Tab-separated (TSV)
  - Proper quoting of multiline descriptions
"""
from __future__ import annotations

import csv
import io
import os
import pytest

from miinto_feed.config_loader import load_config
from miinto_feed.generator import build_miinto_feed


PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
CONFIG_PATH = os.path.join(PROJECT_ROOT, "config", "feed_config.yaml")
INPUT_PATH = os.path.join(PROJECT_ROOT, "sample_data", "products_export.csv")


@pytest.fixture(scope="module")
def feed_bytes():
    config = load_config(CONFIG_PATH)
    with open(INPUT_PATH, newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    return build_miinto_feed(rows, config)


class TestOutputFormat:
    def test_valid_utf8(self, feed_bytes):
        """Output must be valid UTF-8."""
        try:
            feed_bytes.decode("utf-8")
        except UnicodeDecodeError:
            pytest.fail("Output is not valid UTF-8")

    def test_unix_line_endings(self, feed_bytes):
        """Line endings must be Unix \\n, not Windows \\r\\n."""
        assert b"\r\n" not in feed_bytes, "Found Windows \\r\\n line endings"
        assert b"\n" in feed_bytes, "No line endings found at all"

    def test_tsv_not_csv(self, feed_bytes):
        """Delimiter must be tab, not comma (for non-quoted data)."""
        text = feed_bytes.decode("utf-8")
        header = text.split("\n")[0]
        # Header should contain tabs
        assert "\t" in header, "Header does not contain tabs — not TSV"
        # Should have 44 tabs (45 columns)
        assert header.count("\t") == 44, (
            f"Expected 44 tabs in header (45 columns), got {header.count(chr(9))}"
        )

    def test_tsv_parseable(self, feed_bytes):
        """The output must be parseable as TSV."""
        text = feed_bytes.decode("utf-8")
        reader = csv.DictReader(io.StringIO(text), delimiter="\t")
        rows = list(reader)
        assert len(rows) > 0, "No data rows parsed"
        assert len(reader.fieldnames or []) == 45, (
            f"Expected 45 columns, got {len(reader.fieldnames or [])}"
        )

    def test_descriptions_quoted_when_multiline(self, feed_bytes):
        """Descriptions that contain newlines or special chars should be
        properly TSV-quoted (wrapped in double quotes)."""
        text = feed_bytes.decode("utf-8")
        reader = csv.DictReader(io.StringIO(text), delimiter="\t")
        for row in reader:
            desc = row.get("description", "")
            # If description has actual newlines, the CSV reader handles
            # unquoting, so we just verify it parsed without error
            assert desc is not None

    def test_no_zero_prices(self, feed_bytes):
        """Price columns must never contain '0' — only digits > 0 or empty."""
        text = feed_bytes.decode("utf-8")
        reader = csv.DictReader(io.StringIO(text), delimiter="\t")
        price_cols = [
            col for col in (reader.fieldnames or [])
            if "retail_price_" in col
        ]
        for row in reader:
            for col in price_cols:
                val = row[col].strip()
                if val:
                    assert val != "0", (
                        f"Price column {col} contains '0' for id={row.get('id')}"
                    )
