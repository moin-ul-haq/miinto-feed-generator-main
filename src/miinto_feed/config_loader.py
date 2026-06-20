"""
Load and merge all configuration needed by the feed generator.

Reads:
  - feed_config.yaml   → currencies, languages, constants, feed settings
  - fx_rates.csv        → {currency: eur_rate}
  - vat_rates.csv       → {currency: vat_pct}
  - category_map.csv    → {shopify_path: miinto_product_type}

Returns a single dict consumed by ``build_miinto_feed``.
"""
from __future__ import annotations

import csv
import os
from typing import Any, Dict

import yaml


def _normalise_category_key(key: str) -> str:
    """Normalise whitespace around '>' in category paths for robust matching."""
    return " > ".join(part.strip() for part in key.split(">"))


def load_csv_map(path: str, key_col: str, val_col: str) -> Dict[str, str]:
    """Read a two-column CSV into a dict."""
    result: Dict[str, str] = {}
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            result[row[key_col].strip()] = row[val_col].strip()
    return result


def load_fx_rates(path: str) -> Dict[str, float]:
    """Load FX rates as {currency: float}."""
    raw = load_csv_map(path, "currency", "eur_rate")
    return {k: float(v) for k, v in raw.items()}


def load_vat_rates(path: str) -> Dict[str, float]:
    """Load VAT percentages as {currency: float}."""
    raw = load_csv_map(path, "currency", "vat_pct")
    return {k: float(v) for k, v in raw.items()}


def load_category_map(path: str) -> Dict[str, str]:
    """Load Shopify → Miinto category mapping with normalised keys."""
    raw = load_csv_map(path, "shopify_category_path", "miinto_product_type")
    return {_normalise_category_key(k): v for k, v in raw.items()}


def load_config(config_path: str) -> Dict[str, Any]:
    """Load the master config YAML and resolve paths to supporting CSVs.

    The returned dict contains everything the generator needs:
      - ``currencies``, ``languages``, ``constants``, ``feed``, ``stock``
        directly from the YAML
      - ``fx_rates``     – {currency: eur_rate}
      - ``vat_rates``    – {currency: vat_pct}
      - ``category_map`` – {normalised_shopify_path: miinto_type}
      - ``pricing``      – pricing settings from the YAML
    """
    with open(config_path, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)

    config_dir = os.path.dirname(os.path.abspath(config_path))

    # Load supporting CSVs (expected in the same directory as the YAML)
    fx_path = os.path.join(config_dir, "fx_rates.csv")
    vat_path = os.path.join(config_dir, "vat_rates.csv")
    # category_map lives in ../mapping/ relative to config/
    project_root = os.path.dirname(config_dir)
    cat_path = os.path.join(project_root, "mapping", "category_map.csv")

    cfg["fx_rates"] = load_fx_rates(fx_path)
    cfg["vat_rates"] = load_vat_rates(vat_path)
    cfg["category_map"] = load_category_map(cat_path)

    return cfg
