"""
WSGI entry point for hosting the Miinto feed on Render / Gunicorn.

Generates the feed once at startup from the bundled sample data + config,
then serves it at ``/miinto_feed.tsv``.

Render config:
  Build command:  pip install -r requirements.txt
  Start command:  gunicorn serve:app --bind 0.0.0.0:$PORT
"""
from __future__ import annotations

import csv
import os

from flask import Flask, Response

from miinto_feed.config_loader import load_config
from miinto_feed.generator import build_miinto_feed

# ---------------------------------------------------------------------------
# Generate the feed once at import time (Gunicorn worker startup)
# ---------------------------------------------------------------------------

_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
_CONFIG_PATH = os.path.join(_PROJECT_ROOT, "config", "feed_config.yaml")
_INPUT_PATH = os.path.join(_PROJECT_ROOT, "sample_data", "products_export.csv")


def _generate() -> bytes:
    config = load_config(_CONFIG_PATH)
    with open(_INPUT_PATH, newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    return build_miinto_feed(rows, config)


FEED_BYTES = _generate()

# ---------------------------------------------------------------------------
# Flask app
# ---------------------------------------------------------------------------

app = Flask(__name__)


@app.route("/miinto_feed.tsv")
def serve_feed():
    """Serve the feed — no auth for FAS trial validation."""
    return Response(
        FEED_BYTES,
        mimetype="text/tab-separated-values; charset=utf-8",
        headers={
            "Content-Disposition": 'inline; filename="miinto_feed.tsv"',
            "Cache-Control": "public, max-age=300",
        },
    )


@app.route("/")
def index():
    size_kb = len(FEED_BYTES) / 1024
    lines = FEED_BYTES.count(b"\n")
    return Response(
        f"Miinto feed server. Feed: /miinto_feed.tsv ({size_kb:.1f} KB, {lines} lines)",
        mimetype="text/plain",
    )
