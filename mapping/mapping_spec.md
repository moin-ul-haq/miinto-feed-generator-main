# Mapping Spec — source column → Miinto column

At-a-glance correspondence. Exact transform logic is in **`../rules_cheatsheet.md`**.
Source columns are the headers of `../sample_data/products_export.csv`.
`<CUR>` ∈ {NOK,DKK,SEK,EUR,PLN,GBP,CNY}; `<lang>` ∈ {DA,SV,NO,NL,EN,DE,PL,FI,ES,FR,IT}.

| Miinto column | ← source column | transform |
|---|---|---|
| `id` | `variant_gid` | strip `gid://…/` prefix |
| `item_group_id` | `product_gid` | strip `gid://…/` prefix |
| `c:style_id:string` | `mpn` | passthrough |
| `brand` | `vendor` | passthrough |
| `title` | `title` | passthrough |
| `color` | `colour` | passthrough |
| `size` | `size` | passthrough |
| `image_link` | `images` | first URL, %-encode |
| `additional_image_link` | `images` | rest, %-encode, join `,` |
| `c:stock_level:integer` | `stock` | integer ≥ 0 |
| `c:retail_price_<CUR>:integer` | `price_eur_net` | × fx × (1+vat); integer cents |
| `c:discount_retail_price_<CUR>:integer` | `compare_at_price` | same; empty if none |
| `material` | `material_upper` | JSON: `{"en_EN.utf8":"Upper composition: …. "}` |
| `gtin` | `barcode` | digits; empty allowed |
| `c:title_EN:string` | `title` | passthrough |
| `product_type` | `shopify_category` | lookup in `category_map.csv` |
| `gender` | `gender_raw` | Men/Boys→M, Women/Girls→F |
| `c:season_tag:string` | `season_raw` | swap YY/SS |
| `description` | `description_html` | strip HTML → plain text |
| `c:description_<lang>:string` | `description_html` | strip HTML (same as EN) |
| `washing` | — | config constant (JSON) |
| `hs_code` | `hs_code` | passthrough |
| `madein` | `country_of_origin` | passthrough |

Canonical column **order** = the header of `../reference/reference_feed.tsv`.
