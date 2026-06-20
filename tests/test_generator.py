"""
Integration tests for the feed generator.

Tests the full pipeline: config loading → row transform → TSV output.
Uses the actual sample data and config files from the repo.
"""
from __future__ import annotations

import csv
import io
import os
import pytest
from typing import Dict, List

from miinto_feed.config_loader import load_config
from miinto_feed.generator import build_miinto_feed, build_column_order


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
CONFIG_PATH = os.path.join(PROJECT_ROOT, "config", "feed_config.yaml")
INPUT_PATH = os.path.join(PROJECT_ROOT, "sample_data", "products_export.csv")
REFERENCE_PATH = os.path.join(PROJECT_ROOT, "reference", "reference_feed.tsv")


@pytest.fixture(scope="module")
def config():
    return load_config(CONFIG_PATH)


@pytest.fixture(scope="module")
def input_rows():
    with open(INPUT_PATH, newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


@pytest.fixture(scope="module")
def feed_bytes(input_rows, config):
    return build_miinto_feed(input_rows, config)


@pytest.fixture(scope="module")
def feed_lines(feed_bytes):
    text = feed_bytes.decode("utf-8")
    return text.split("\n")


@pytest.fixture(scope="module")
def reference_header():
    with open(REFERENCE_PATH, encoding="utf-8") as fh:
        first_line = fh.readline().rstrip("\n").rstrip("\r")
    return first_line.split("\t")


# ---------------------------------------------------------------------------
# Column / header tests
# ---------------------------------------------------------------------------

class TestColumnHeader:
    def test_column_count_is_45(self, config):
        """The feed must have exactly 45 columns."""
        cols = build_column_order(config)
        assert len(cols) == 45

    def test_header_matches_reference(self, feed_lines, reference_header):
        """Our header must match the reference feed's header exactly."""
        our_header = feed_lines[0].split("\t")
        assert our_header == reference_header, (
            f"Header mismatch.\n"
            f"Ours:      {our_header}\n"
            f"Reference: {reference_header}"
        )

    def test_dynamic_currency_columns_present(self, config):
        """All 7 currencies × 2 (retail + discount) = 14 price columns."""
        cols = build_column_order(config)
        currencies = config["currencies"]
        for cur in currencies:
            assert f"c:retail_price_{cur}:integer" in cols
            assert f"c:discount_retail_price_{cur}:integer" in cols

    def test_dynamic_language_columns_present(self, config):
        """All 11 description languages + 1 title language present."""
        cols = build_column_order(config)
        for lang in config["languages"]["description"]:
            assert f"c:description_{lang}:string" in cols
        for lang in config["languages"]["title"]:
            assert f"c:title_{lang}:string" in cols


# ---------------------------------------------------------------------------
# Row count / variant grouping
# ---------------------------------------------------------------------------

class TestVariantGrouping:
    def test_row_count_matches_input(self, feed_lines, input_rows):
        """One output row per input variant row (+ 1 header)."""
        # Last line might be empty from trailing newline
        data_lines = [l for l in feed_lines if l.strip()]
        # Header + data rows
        assert len(data_lines) == len(input_rows) + 1

    def test_variants_share_item_group_id(self, feed_bytes):
        """Variants of the same product must share item_group_id."""
        reader = csv.DictReader(
            io.StringIO(feed_bytes.decode("utf-8")),
            delimiter="\t",
        )
        rows_by_group: Dict[str, List[dict]] = {}
        for row in reader:
            gid = row["item_group_id"]
            rows_by_group.setdefault(gid, []).append(row)

        # Spot-check: at least one group has >1 variant
        multi_variant = {k: v for k, v in rows_by_group.items() if len(v) > 1}
        assert len(multi_variant) > 0, "Expected some products with multiple variants"

        # For multi-variant groups, brand/title/color should be consistent
        for gid, variants in multi_variant.items():
            brands = {v["brand"] for v in variants}
            assert len(brands) == 1, f"Group {gid} has inconsistent brands: {brands}"


# ---------------------------------------------------------------------------
# Price columns
# ---------------------------------------------------------------------------

class TestPriceColumns:
    def test_prices_are_integer_or_empty(self, feed_bytes):
        """All price cells must be either empty or a positive integer (never '0' for absent)."""
        reader = csv.DictReader(
            io.StringIO(feed_bytes.decode("utf-8")),
            delimiter="\t",
        )
        price_cols = [
            col for col in reader.fieldnames or []
            if "retail_price_" in col
        ]
        for row in reader:
            for col in price_cols:
                val = row[col]
                if val:
                    assert val.isdigit(), f"Price column {col} has non-integer value: {val!r}"
                    assert int(val) > 0, f"Price column {col} has zero value"


# ---------------------------------------------------------------------------
# Static fields match reference (spot-check)
# ---------------------------------------------------------------------------

class TestReferenceMatch:
    def test_stable_fields_for_known_variant(self, feed_bytes):
        """For a known variant ID, stable fields should match expected values."""
        reader = csv.DictReader(
            io.StringIO(feed_bytes.decode("utf-8")),
            delimiter="\t",
        )
        # Look for variant 47762944754007 (Dsquared2 Plaque Belts, size 80)
        target_id = "47762944754007"
        target_row = None
        for row in reader:
            if row["id"] == target_id:
                target_row = row
                break

        assert target_row is not None, f"Variant {target_id} not found in output"
        assert target_row["brand"] == "Dsquared2"
        assert target_row["title"] == "Plaque Belts"
        assert target_row["color"] == "Black"
        assert target_row["gender"] == "F"
        assert target_row["c:season_tag:string"] == "SS21"
        assert target_row["madein"] == "IT"
        assert target_row["gtin"] == "8058097862027"
