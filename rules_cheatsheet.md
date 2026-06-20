# Rules Cheatsheet — building the Miinto feed

Exact transform for every Miinto column, from the columns in
`sample_data/products_export.csv`. The **canonical column set + order** is the
header of `reference/reference_feed.tsv` (45 columns) — match it exactly
(case-sensitive). Validate against that reference (stable fields should match per
variant id; **prices and `c:stock_level` will differ** — point-in-time snapshot — and
description whitespace may vary) and against FAS (`https://proxy-fas.miinto.net/feed`,
type `shop`).

## ID & grouping
- `id` ← `variant_gid`, **strip the `gid://shopify/ProductVariant/` prefix** → numeric. e.g. `gid://shopify/ProductVariant/47731131711831` → `47731131711831`.
- `item_group_id` ← `product_gid`, strip `gid://shopify/Product/` prefix → numeric.

## Direct passthrough
`c:style_id:string`←`mpn` · `brand`←`vendor` · `title`←`title` · `c:title_EN:string`←`title` · `color`←`colour` · `size`←`size` · `gtin`←`barcode` (digits only; ~6% blank → leave empty) · `hs_code`←`hs_code` · `madein`←`country_of_origin` · `c:stock_level:integer`←`stock` (integer ≥ 0; keep `0`, don't drop the row).

## Images — split + percent-encode
Input `images` = URLs separated by `", "` (comma-space).
- `image_link` ← **first** URL, percent-encoded.
- `additional_image_link` ← the **rest**, each percent-encoded, joined by `,` (comma, no space). Empty if only one image (~50%).

## Gender — map  (`gender` ← `gender_raw`)
`Men`→`M`, `Boys`→`M`, `Women`→`F`, `Girls`→`F`. (Miinto has no kids gender; kids are signalled via `product_type`.)

## Season — swap  (`c:season_tag:string` ← `season_raw`)
Swap the year/season halves: `s[2:] + s[:2]`. `22AW`→`AW22`, `23SS`→`SS23`.

## Category — lookup  (`product_type` ← `shopify_category`)
Look `shopify_category` up in `mapping/category_map.csv`
(`shopify_category_path` → `miinto_product_type`). Leave empty if not found (it's optional). Match keys exact (or normalise spaces around `>`).

## Material — wrap, upper only  (`material` ← `material_upper`)
JSON: `{"en_EN.utf8":"Upper composition: <material_upper>. "}` — note the trailing `". "`. Upper composition only (ignore inner/sole). If `material_upper` is empty, leave `material` empty.

## Description — strip HTML, duplicate to all languages
- `description` ← `description_html` with **HTML tags removed** → plain text. Wrap multiline values in `"`.
- `c:description_<lang>:string` for **all** configured languages (DA, SV, NO, NL, EN, DE, PL, FI, ES, FR, IT) ← the **same** plain-text description.

## Washing — constant
`washing` ← the config constant (JSON): `{"en_EN.utf8":"Wash with care. See product labels for further instructions"}`.

## Prices — compute, config-driven  (**values need not match the reference**)
For each currency in `config/feed_config.yaml`:
- `c:retail_price_<CUR>:integer` ← `price_eur_net × fx_rate[CUR] × (1 + vat_pct[CUR]/100)`, round to 2 dp, then **embed as integer cents** (e.g. `263.43` → `26343`).
  - `fx_rate` from `config/fx_rates.csv`, `vat_pct` from `config/vat_rates.csv`.
- `c:discount_retail_price_<CUR>:integer` ← same formula on `compare_at_price` **if present**; otherwise **empty** (never `0`). TOPS `compare_at_price` is usually empty → discount columns blank. (The reference feed's discounts come from Koongo's own pricing engine and are out of scope.)
- Any absent price → **empty cell, never `0`**.

## Output rules
- TSV, UTF-8, Unix `\n`, header row; **all 45 columns**, exact case-sensitive names, in the reference's order.
- One row per variant; variants of a product share `item_group_id`.
- Dedup key `item_group_id`+`size`+`color`+`brand` must be unique.
- Immutable once live: `item_group_id`, `brand`, `color`, `size`.
