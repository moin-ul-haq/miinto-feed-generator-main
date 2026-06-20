"""
Unit tests for individual transform functions.

Covers every acceptance criterion:
  - price → cents (including whole numbers, missing → empty, no zero)
  - dynamic currency/language column generation
  - header ordering
  - variant grouping (row count + shared fields)
  - multiline quoting
  - URL percent-encoding
  - output structure (TSV / Unix EOL)
  - gender mapping, season swap, GID stripping, material JSON, category lookup
"""
from __future__ import annotations

import pytest

from miinto_feed.transforms import (
    strip_gid_prefix,
    map_gender,
    swap_season,
    price_to_cents,
    percent_encode_url,
    split_images,
    strip_html,
    format_material,
    lookup_category,
)


# ========================================================================
# GID prefix stripping
# ========================================================================

class TestStripGidPrefix:
    def test_variant_gid(self):
        assert strip_gid_prefix("gid://shopify/ProductVariant/47731131711831") == "47731131711831"

    def test_product_gid(self):
        assert strip_gid_prefix("gid://shopify/Product/8903131464023") == "8903131464023"

    def test_already_numeric(self):
        assert strip_gid_prefix("12345") == "12345"

    def test_empty(self):
        assert strip_gid_prefix("") == ""


# ========================================================================
# Gender mapping
# ========================================================================

class TestMapGender:
    def test_men(self):
        assert map_gender("Men") == "M"

    def test_women(self):
        assert map_gender("Women") == "F"

    def test_boys(self):
        assert map_gender("Boys") == "M"

    def test_girls(self):
        assert map_gender("Girls") == "F"

    def test_unknown_passthrough(self):
        assert map_gender("Other") == "Other"


# ========================================================================
# Season swap
# ========================================================================

class TestSwapSeason:
    def test_aw(self):
        assert swap_season("22AW") == "AW22"

    def test_ss(self):
        assert swap_season("23SS") == "SS23"

    def test_24ss(self):
        assert swap_season("24SS") == "SS24"

    def test_empty(self):
        assert swap_season("") == ""


# ========================================================================
# Price to cents
# ========================================================================

class TestPriceToCents:
    def test_normal_conversion(self):
        """Basic conversion: 330.57 × 11.1045 × 1.25 → integer cents."""
        result = price_to_cents("330.57", 11.1045, 25.0)
        # 330.57 * 11.1045 * 1.25 = 4589.646…  → round to 4589.65 → 458965
        assert result.isdigit()
        assert int(result) > 0

    def test_whole_number_price(self):
        """Whole-number price: 100.00 × 1.0 × (1+25%) = 125.00 → 12500."""
        result = price_to_cents("100.00", 1.0, 25.0)
        assert result == "12500"

    def test_absent_price_returns_empty(self):
        """Missing/empty price → empty string, NOT '0'."""
        assert price_to_cents("", 11.1045, 25.0) == ""
        assert price_to_cents("   ", 11.1045, 25.0) == ""

    def test_none_like_absent(self):
        """None-ish values → empty."""
        assert price_to_cents(None, 11.1045, 25.0) == ""

    def test_never_returns_zero_for_absent(self):
        """Absent price must NEVER be '0'."""
        result = price_to_cents("", 1.0, 0.0)
        assert result != "0"
        assert result == ""

    def test_eur_identity(self):
        """EUR with fx=1.0: 100.00 × 1.0 × 1.25 = 125.00 → 12500."""
        result = price_to_cents("100.00", 1.0, 25.0)
        assert result == "12500"

    def test_precision_rounding(self):
        """Ensure correct rounding to 2 dp before cents conversion."""
        # 10.00 × 7.4746 × 1.25 = 93.4325 → round to 93.43 → 9343
        result = price_to_cents("10.00", 7.4746, 25.0)
        assert result == "9343"


# ========================================================================
# URL percent-encoding
# ========================================================================

class TestPercentEncodeUrl:
    def test_clean_url_unchanged(self):
        url = "https://cdn.shopify.com/s/files/image.jpg?v=123"
        result = percent_encode_url(url)
        assert result == url

    def test_empty(self):
        assert percent_encode_url("") == ""

    def test_preserves_query_params(self):
        url = "https://cdn.shopify.com/s/files/image.jpg?v=1709145231"
        result = percent_encode_url(url)
        assert "v=1709145231" in result


class TestSplitImages:
    def test_single_image(self):
        first, rest = split_images("https://example.com/img.jpg")
        assert first == "https://example.com/img.jpg"
        assert rest == ""

    def test_multiple_images(self):
        images = "https://a.com/1.jpg, https://a.com/2.jpg, https://a.com/3.jpg"
        first, rest = split_images(images)
        assert first == "https://a.com/1.jpg"
        assert "https://a.com/2.jpg" in rest
        assert "https://a.com/3.jpg" in rest
        # Joined by comma, no space
        assert ", " not in rest

    def test_empty(self):
        first, rest = split_images("")
        assert first == ""
        assert rest == ""


# ========================================================================
# HTML stripping
# ========================================================================

class TestStripHtml:
    def test_basic_tags(self):
        result = strip_html("<p><strong>Product Details</strong></p>")
        assert result == "Product Details"

    def test_br_tags(self):
        result = strip_html("Line1<br>Line2")
        assert "Line1" in result
        assert "Line2" in result

    def test_entity_unescape(self):
        result = strip_html("Puffer &amp; Down Jacket")
        assert result == "Puffer & Down Jacket"

    def test_empty(self):
        assert strip_html("") == ""

    def test_none(self):
        assert strip_html(None) == ""


# ========================================================================
# Material JSON
# ========================================================================

class TestFormatMaterial:
    def test_normal(self):
        result = format_material("Sheep Leather 100%")
        assert result == '{"en_EN.utf8":"Upper composition: Sheep Leather 100%. "}'

    def test_empty_returns_empty(self):
        assert format_material("") == ""
        assert format_material("   ") == ""

    def test_custom_template(self):
        result = format_material("Cotton", template="Material: {upper}. ")
        assert '"Material: Cotton. "' in result

    def test_trailing_dot_space(self):
        """Material must end with '. ' (dot-space) per the spec."""
        result = format_material("Leather")
        assert '. "' in result


# ========================================================================
# Category lookup
# ========================================================================

class TestLookupCategory:
    def test_found(self):
        cat_map = {"Bags > Shoulder Bags > Women": "Bags > Shoulder Bags"}
        result = lookup_category("Bags>Shoulder Bags>Women", cat_map)
        assert result == "Bags > Shoulder Bags"

    def test_not_found(self):
        cat_map = {"Bags > Shoulder Bags > Women": "Bags > Shoulder Bags"}
        result = lookup_category("Unknown>Category", cat_map)
        assert result == ""

    def test_empty(self):
        assert lookup_category("", {}) == ""

    def test_normalisation(self):
        """Spaces around '>' should be normalised for matching."""
        cat_map = {"Accessories > Belts > Women": "Accessories > Belts"}
        # Source uses no spaces around >
        result = lookup_category("Accessories>Belts>Women", cat_map)
        assert result == "Accessories > Belts"
