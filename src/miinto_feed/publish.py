"""
Hosting / delivery: make the generated feed reachable for Miinto to pull.

Miinto fetches the feed over HTTP(S) every 30 minutes, authenticated with HTTP
Basic Auth, from a FIXED filename/URL (full feed each time, no deltas).

For this trial: host on YOUR OWN environment and validate via FAS
(https://proxy-fas.miinto.net/feed). Production hosting is handled on the client
side afterwards.
"""
from __future__ import annotations

import os
import threading
from typing import Any, Mapping

from flask import Flask, Response, request


def _create_app(feed_bytes: bytes, filename: str = "miinto_feed.tsv") -> Flask:
    """Create a minimal Flask app that serves the feed file."""
    app = Flask(__name__)

    @app.route(f"/{filename}")
    def serve_feed():  # type: ignore[no-untyped-def]
        """Serve the feed TSV file.

        No auth for the trial — FAS has no auth field.
        """
        return Response(
            feed_bytes,
            mimetype="text/tab-separated-values; charset=utf-8",
            headers={
                "Content-Disposition": f'inline; filename="{filename}"',
            },
        )

    @app.route("/")
    def index():  # type: ignore[no-untyped-def]
        """Health-check / info endpoint."""
        size_kb = len(feed_bytes) / 1024
        return Response(
            f"Miinto feed server running. Feed: /{filename} ({size_kb:.1f} KB)",
            mimetype="text/plain",
        )

    return app


def publish_feed(feed_bytes: bytes, hosting: Mapping[str, Any]) -> str:
    """Write/serve the feed and return the local URL.

    For the trial: serve over HTTP at a fixed filename so you can tunnel
    it via ngrok to get an HTTPS URL for FAS validation.

    Args:
        feed_bytes: The feed TSV content.
        hosting:    Configuration dict with keys:
                    - output_path (str): where to write the file
                    - host (str): bind host (default 0.0.0.0)
                    - port (int): bind port (default 8080)

    Returns:
        The local URL where the feed is served.
    """
    host = hosting.get("host", "0.0.0.0")
    port = hosting.get("port", 8080)
    filename = "miinto_feed.tsv"

    # Also write to disk at the output path
    output_path = hosting.get("output_path", f"output/{filename}")
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "wb") as fh:
        fh.write(feed_bytes)

    app = _create_app(feed_bytes, filename)

    print(f"\n  Feed server starting on http://{host}:{port}/{filename}")
    print("  Use ngrok or similar to expose as HTTPS for FAS validation.")
    print("  Press Ctrl+C to stop.\n")

    # Run Flask (blocking)
    app.run(host=host, port=port, debug=False)

    return f"http://{host}:{port}/{filename}"
