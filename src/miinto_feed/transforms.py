"""
Pure transform functions — one per Miinto column rule.

Every function is stateless and independently testable.
See ``rules_cheatsheet.md`` for the spec behind each transform.
"""
from __future__ import annotations

import html as _html
import json
import re
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote as _url_quote, urlparse, urlunparse


# ---------------------------------------------------------------------------
# ID & grouping
# ---------------------------------------------------------------------------

_GID_PREFIX_RE = re.compile(r"^gid://shopify/\w+/")


def strip_gid_prefix(gid: str) -> str:
    """Strip the ``gid://shopify/…/`` prefix, returning the numeric id.

    >>> strip_gid_prefix("gid://shopify/ProductVariant/47731131711831")
    '47731131711831'
    """
    return _GID_PREFIX_RE.sub("", gid)


# ---------------------------------------------------------------------------
# Gender mapping
# ---------------------------------------------------------------------------

_GENDER_MAP = {"Men": "M", "Boys": "M", "Women": "F", "Girls": "F"}


def map_gender(raw: str) -> str:
    """Map source gender to Miinto code (M/F).

    >>> map_gender("Women")
    'F'
    """
    return _GENDER_MAP.get(raw, raw)


# ---------------------------------------------------------------------------
# Season swap
# ---------------------------------------------------------------------------

def swap_season(raw: str) -> str:
    """Swap year/season halves: ``22AW`` → ``AW22``.

    >>> swap_season("22AW")
    'AW22'
    """
    if not raw:
        return ""
    return raw[2:] + raw[:2]


# ---------------------------------------------------------------------------
# Images — split & percent-encode
# ---------------------------------------------------------------------------

def percent_encode_url(url: str) -> str:
    """Percent-encode special characters in a URL's path/query while
    preserving the scheme, host, and existing %-sequences.

    This uses ``urllib.parse.quote`` with ``safe`` chars that are valid in URLs
    but encodes anything else (spaces, non-ASCII, etc.).
    """
    url = url.strip()
    if not url:
        return ""
    parsed = urlparse(url)
    # Encode path components but keep / and existing %XX
    encoded_path = _url_quote(parsed.path, safe="/:@!$&'()*+,;=-._~")
    # Encode query keeping = and &
    encoded_query = _url_quote(parsed.query, safe="/:@!$&'()*+,;=-._~?")
    return urlunparse((
        parsed.scheme,
        parsed.netloc,
        encoded_path,
        parsed.params,
        encoded_query,
        parsed.fragment,
    ))


def split_images(images_str: str) -> Tuple[str, str]:
    """Split the ``images`` field (URLs separated by ``", "``) into
    ``(image_link, additional_image_link)``.

    Both are percent-encoded.  ``additional_image_link`` URLs are joined by
    ``,`` (comma, no space).  Empty if only one image.
    """
    if not images_str:
        return ("", "")
    urls = [u.strip() for u in images_str.split(", ")]
    urls = [u for u in urls if u]  # drop empties
    if not urls:
        return ("", "")
    first = percent_encode_url(urls[0])
    rest = ",".join(percent_encode_url(u) for u in urls[1:]) if len(urls) > 1 else ""
    return (first, rest)


# ---------------------------------------------------------------------------
# Price computation
# ---------------------------------------------------------------------------

def price_to_cents(
    eur_net: str,
    fx_rate: float,
    vat_pct: float,
) -> str:
    """Convert a EUR net price to integer cents for a target currency.

    Formula: ``eur_net × fx_rate × (1 + vat_pct / 100)``
    Round to 2 decimal places, then embed as integer cents.

    Returns an **empty string** if ``eur_net`` is missing/blank.
    Never returns ``"0"`` for absent prices.

    >>> price_to_cents("330.57", 11.1045, 25.0)
    '458965'
    """
    if not eur_net or not eur_net.strip():
        return ""
    val = Decimal(eur_net.strip())
    rate = Decimal(str(fx_rate))
    vat_mult = Decimal("1") + Decimal(str(vat_pct)) / Decimal("100")
    result = val * rate * vat_mult
    # Round to 2 decimal places
    result = result.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    # Convert to integer cents
    cents = int(result * 100)
    return str(cents)


# ---------------------------------------------------------------------------
# HTML stripping
# ---------------------------------------------------------------------------

_TAG_RE = re.compile(r"<[^>]+>")


def strip_html(html_str: str) -> str:
    """Remove HTML tags and unescape entities → plain text.

    >>> strip_html("<p><strong>Product</strong></p>")
    'Product'
    """
    if not html_str:
        return ""
    text = _TAG_RE.sub("", html_str)
    text = _html.unescape(text)
    return text


# ---------------------------------------------------------------------------
# Material JSON
# ---------------------------------------------------------------------------

def format_material(upper: str, template: str = "Upper composition: {upper}. ") -> str:
    """Wrap the upper composition in the Miinto JSON format.

    Returns empty string if ``upper`` is blank.

    >>> format_material("Sheep Leather 100%")
    '{"en_EN.utf8":"Upper composition: Sheep Leather 100%. "}'
    """
    if not upper or not upper.strip():
        return ""
    text = template.replace("{upper}", upper.strip())
    return json.dumps({"en_EN.utf8": text}, ensure_ascii=False, separators=(",", ":"))


# ---------------------------------------------------------------------------
# Category lookup
# ---------------------------------------------------------------------------

def _normalise_category_key(key: str) -> str:
    """Normalise whitespace around '>' in category paths."""
    return " > ".join(part.strip() for part in key.split(">"))


def lookup_category(shopify_cat: str, category_map: Dict[str, str]) -> str:
    """Look up the Miinto product_type for a Shopify category path.

    Keys are normalised (spaces around '>').  Returns empty string if not found.
    """
    if not shopify_cat:
        return ""
    normalised = _normalise_category_key(shopify_cat)
    return category_map.get(normalised, "")


# ---------------------------------------------------------------------------
# Full row transform
# ---------------------------------------------------------------------------

def transform_row(
    row: Dict[str, str],
    config: dict,
    columns: List[str],
) -> Dict[str, str]:
    """Transform a single source CSV row into a dict keyed by Miinto column names.

    Parameters
    ----------
    row : dict
        One row from ``products_export.csv`` (keyed by source column names).
    config : dict
        The merged config from ``config_loader.load_config``.
    columns : list[str]
        The 45-column header list (for initialising empty values).

    Returns
    -------
    dict
        Miinto column name → string value.
    """
    out: Dict[str, str] = {col: "" for col in columns}

    # --- IDs ---
    out["id"] = strip_gid_prefix(row.get("variant_gid", ""))
    out["item_group_id"] = strip_gid_prefix(row.get("product_gid", ""))

    # --- Direct passthrough ---
    out["c:style_id:string"] = row.get("mpn", "")
    out["brand"] = row.get("vendor", "")
    out["title"] = row.get("title", "")
    out["color"] = row.get("colour", "")
    out["size"] = row.get("size", "")
    out["gtin"] = row.get("barcode", "").strip()
    out["hs_code"] = row.get("hs_code", "")
    out["madein"] = row.get("country_of_origin", "")

    # --- Stock ---
    stock_raw = row.get("stock", "")
    out["c:stock_level:integer"] = stock_raw.strip() if stock_raw.strip() else "0"

    # --- Images ---
    image_link, additional = split_images(row.get("images", ""))
    out["image_link"] = image_link
    out["additional_image_link"] = additional

    # --- Gender ---
    out["gender"] = map_gender(row.get("gender_raw", ""))

    # --- Season ---
    out["c:season_tag:string"] = swap_season(row.get("season_raw", ""))

    # --- Category ---
    out["product_type"] = lookup_category(
        row.get("shopify_category", ""),
        config["category_map"],
    )

    # --- Material ---
    template = config.get("constants", {}).get(
        "material_template", "Upper composition: {upper}. "
    )
    out["material"] = format_material(row.get("material_upper", ""), template)

    # --- Description (HTML → plain text, duplicated to all languages) ---
    desc_plain = strip_html(row.get("description_html", ""))
    out["description"] = desc_plain
    for lang in config.get("languages", {}).get("description", []):
        col_name = f"c:description_{lang}:string"
        if col_name in out:
            out[col_name] = desc_plain

    # --- Title (per-language) ---
    title_val = row.get("title", "")
    for lang in config.get("languages", {}).get("title", []):
        col_name = f"c:title_{lang}:string"
        if col_name in out:
            out[col_name] = title_val

    # --- Washing (constant) ---
    out["washing"] = config.get("constants", {}).get("washing", "")

    # --- Prices ---
    fx_rates = config.get("fx_rates", {})
    vat_rates = config.get("vat_rates", {})
    eur_net = row.get("price_eur_net", "")
    compare_at = row.get("compare_at_price", "")

    for cur in config.get("currencies", []):
        fx = fx_rates.get(cur, 1.0)
        vat = vat_rates.get(cur, 0.0)

        retail_col = f"c:retail_price_{cur}:integer"
        discount_col = f"c:discount_retail_price_{cur}:integer"

        if retail_col in out:
            out[retail_col] = price_to_cents(eur_net, fx, vat)

        if discount_col in out:
            out[discount_col] = price_to_cents(compare_at, fx, vat)

    return out
