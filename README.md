# Miinto Product Feed Generator

A Python tool that transforms our product/variant data into a **Miinto-compliant
TSV product feed**, hosts it at an HTTPS URL, and validates clean in
Miinto's **FAS** (Feed Analysis Service).

Everything you need is in this repo — no access to our systems required.

## What you're building
1. A **generator**: read `sample_data/products_export.csv` and emit a valid Miinto TSV.
2. **Hosting**: serve the file at a fixed HTTPS URL (your own host for the trial). Miinto's *production* pull uses HTTP Basic Auth; for the trial, host without auth so FAS can validate it.
3. **Validation**: pass **FAS** (`https://proxy-fas.miinto.net/feed`, feed type `shop`) with no blocking errors, and match the reference feed's structure.

You don't need product/catalogue knowledge — all mapping decisions are resolved
for you in the data + the rules below.

## What's in the repo
| Path | What it is |
|---|---|
| `sample_data/products_export.csv` | **Input** — real export, 1 row/variant, 221 rows / 70 products |
| `reference/reference_feed.tsv` | **Answer key** — our live Miinto feed for the *same* 70 products. Stable fields should match per variant id (prices & stock differ — it's a snapshot) |
| `mapping/mapping_spec.md` | Source column → Miinto column table |
| `rules_cheatsheet.md` | The exact transform for every column |
| `mapping/category_map.csv` | `product_type` lookup (shopify path → Miinto category) |
| `config/feed_config.yaml` | Currencies, languages, constants |
| `config/vat_rates.csv`, `config/fx_rates.csv` | Per-currency lookups (prices needn't match — seeded) |
| `docs/miinto-feed-spec.md` | The Miinto feed spec (format, hosting, rules) |
| `src/miinto_feed/` | Interface stubs to implement (`generator`, `publish`, `cli`) |
| `ACCEPTANCE.md` | Definition of done |

## Running (target UX)
```
python -m miinto_feed --config config/feed_config.yaml \
                      --input  sample_data/products_export.csv \
                      --output output/miinto_feed.tsv
```

## Validate
1. Host `output/miinto_feed.tsv` at a reachable **HTTPS URL** and submit it to
   `https://proxy-fas.miinto.net/feed` (feed type `shop`); resolve any blocking errors.
   FAS only takes a URL (no auth field), so host it **without** Basic Auth for the
   trial — Basic Auth is Miinto's *production* pull requirement, handled on our side.
2. Diff your output against `reference/reference_feed.tsv` (the same 70 products).
   Stable fields — ids, brand, title, color, size, gtin, images, material,
   product_type, gender, season, washing, hs_code, madein — should match **per
   variant id**. Expect differences in **prices** and **c:stock_level** (the reference
   is a point-in-time snapshot), **description whitespace** (HTML stripping varies),
   and ~7% of variants that may not line up 1:1.

## Miinto documentation
- **Feed spec — column headers + rules:** https://miinto-integration.elevio.help/en/articles/3-product-feed-headers
- **Full Product Data docs** (introduction · technical details · headers · example file): https://miinto-integration.elevio.help/en/categories/1-product-data
- **FAS validator:** https://proxy-fas.miinto.net/feed  (feed type `shop`)
- **FAS manual (PDF):** http://files.miinto.com/sample/Miinto_FAS_manual_v1.0.pdf

## Deliverables
Python source, config, unit tests (price encoding, dynamic columns, variant
grouping, quoting, URL encoding, output structure), docs, and the hosted endpoint
— all via **Pull Requests** in this repo.

## Out of scope
Category/attribute mapping (done — it's in the data + `category_map.csv`),
production hosting + connecting the live URL to Miinto, any other marketplace.
