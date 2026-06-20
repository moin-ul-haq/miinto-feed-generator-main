"""
Single-command entrypoint.

Example:
    python -m miinto_feed --config config/feed_config.yaml \\
                          --input  sample_data/products_export.csv \\
                          --output output/miinto_feed.tsv [--publish]
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
from typing import List, Dict, Any

from miinto_feed.config_loader import load_config
from miinto_feed.generator import build_miinto_feed


def _read_input_csv(path: str) -> List[Dict[str, Any]]:
    """Read the source CSV and return a list of row dicts."""
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        return list(reader)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the Miinto product feed.")
    parser.add_argument("--config", required=True, help="Path to feed config YAML")
    parser.add_argument("--input", required=True, help="Path to source product/variant data")
    parser.add_argument("--output", default="output/miinto_feed.tsv", help="Output TSV path")
    parser.add_argument("--publish", action="store_true", help="Host the feed after generating")
    args = parser.parse_args()

    # 1. Load config (YAML + supporting CSVs)
    print(f"Loading config from {args.config} ...")
    config = load_config(args.config)

    # 2. Read input data
    input_path = getattr(args, "input")
    print(f"Reading input from {input_path} ...")
    rows = _read_input_csv(input_path)
    print(f"  -> {len(rows)} variant rows read")

    # 3. Generate the feed
    print("Generating Miinto feed ...")
    feed_bytes = build_miinto_feed(rows, config)

    # 4. Write output
    output_path = args.output
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "wb") as fh:
        fh.write(feed_bytes)
    print(f"  -> Feed written to {output_path} ({len(feed_bytes):,} bytes)")

    # Count stats
    line_count = feed_bytes.count(b"\n")
    print(f"  -> {line_count - 1} data rows + 1 header")

    # 5. Optional: host the feed
    if args.publish:
        from miinto_feed.publish import publish_feed

        hosting_config = {
            "output_path": output_path,
            "host": "0.0.0.0",
            "port": 8080,
        }
        url = publish_feed(feed_bytes, hosting_config)
        print(f"  -> Feed served at {url}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
