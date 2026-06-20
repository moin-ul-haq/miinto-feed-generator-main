# Sample data

`products_export.csv` — a **real** export from our catalogue: **one row per
variant**, 221 rows / 70 products, with product-level fields repeated per row.
Column names here are the contract (see `../mapping/mapping_spec.md`). In
production the same columns come from a DB view; for the trial, build against
this file.

It's deliberately varied: 39 brands, 38 categories, genders Men/Women/Boys/Girls,
multiple seasons, ~6% missing barcodes, single- and multi-variant products,
single- and multi-image products.

**These 70 products are the same ones in `../reference/reference_feed.tsv`** — so you
can diff your output against it. Stable fields (ids, brand, title, colour, size, gtin,
images, category, gender, season, material, washing, hs_code, madein) should match per
variant id; expect **prices** and **stock** to differ (earlier snapshot), description
whitespace to vary, and ~7% of variants not to line up 1:1.

Notes on a few source columns:
- `variant_gid` / `product_gid` are full Shopify GIDs — strip the prefix (see cheatsheet).
- `images` is a single string of URLs separated by `", "` (comma-space).
- `price_eur_net` is the EUR net price; `compare_at_price` is the discount source (usually empty for TOPS).
- `material_upper` is the upper composition string (wrap per the cheatsheet).
- `description_html` is HTML (strip to plain text).
