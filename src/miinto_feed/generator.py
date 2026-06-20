"""
Core feed generation: source rows + config -> Miinto-compliant TSV bytes.

This is the contract to implement. ``build_miinto_feed`` must:

  - read variant rows (see sample_data/) using OUR source field names
  - map each field to its Miinto column per mapping/mapping_spec.md
  - emit a TSV (UTF-8, Unix "\\n" line endings) with a header row containing
    ALL mandatory + optional columns, case-sensitive, in a stable order
  - generate dynamic columns from ``config`` (see config/feed_config.yaml):
        c:retail_price_<CUR>:integer, c:discount_retail_price_<CUR>:integer
        c:title_<lang>:string,        c:description_<lang>:string
  - encode prices as integer cents (1000.99 -> "100099"); empty (NOT "0") when absent
  - emit one row per variant; variants of a product share the same item_group_id
  - quote multiline descriptions; percent-encode special chars in image URLs
  - leave optional values blank where source data is absent

See docs/miinto-feed-spec.md for the full Miinto rules and ACCEPTANCE.md for "done".
"""
from __future__ import annotations

import csv
import io
from typing import Any, Iterable, List, Mapping

from miinto_feed.transforms import transform_row


# ---- The exact 45-column header from reference/reference_feed.tsv ----------
# Order matters — match the reference exactly.

def build_column_order(config: Mapping[str, Any]) -> List[str]:
    """Build the 45-column header list from config.

    The order is fixed to match the reference feed:
      id, item_group_id, c:style_id:string, brand, title, color, size,
      image_link, additional_image_link, c:stock_level:integer,
      <for each currency: discount then retail>,
      material, gtin, c:title_EN:string, product_type, gender,
      c:season_tag:string, description,
      <for each description language: c:description_<lang>:string>,
      washing, hs_code, madein
    """
    cols: List[str] = [
        "id",
        "item_group_id",
        "c:style_id:string",
        "brand",
        "title",
        "color",
        "size",
        "image_link",
        "additional_image_link",
        "c:stock_level:integer",
    ]

    # Price columns — discount BEFORE retail for each currency
    for cur in config.get("currencies", []):
        cols.append(f"c:discount_retail_price_{cur}:integer")
        cols.append(f"c:retail_price_{cur}:integer")

    cols.append("material")
    cols.append("gtin")

    # Title columns (config-driven, typically just EN)
    for lang in config.get("languages", {}).get("title", []):
        cols.append(f"c:title_{lang}:string")

    cols.append("product_type")
    cols.append("gender")
    cols.append("c:season_tag:string")
    cols.append("description")

    # Description columns (config-driven, 11 languages)
    for lang in config.get("languages", {}).get("description", []):
        cols.append(f"c:description_{lang}:string")

    cols.append("washing")
    cols.append("hs_code")
    cols.append("madein")

    return cols


def build_miinto_feed(
    rows: Iterable[Mapping[str, Any]],
    config: Mapping[str, Any],
) -> bytes:
    """Return the Miinto feed as TSV bytes.

    Args:
        rows:   iterable of source variant rows (our field names — see mapping spec).
        config: parsed feed config (currencies, languages, feed settings).

    Returns:
        The complete feed as UTF-8 TSV bytes, ready to host.
    """
    columns = build_column_order(config)

    buf = io.StringIO()
    writer = csv.writer(
        buf,
        delimiter="\t",
        quoting=csv.QUOTE_MINIMAL,
        lineterminator="\n",
        quotechar='"',
    )

    # Header row
    writer.writerow(columns)

    # Data rows — one per variant
    for row in rows:
        transformed = transform_row(dict(row), dict(config), columns)
        writer.writerow([transformed.get(col, "") for col in columns])

    return buf.getvalue().encode("utf-8")
