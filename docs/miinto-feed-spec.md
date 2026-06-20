# Miinto Product Feed — Technical Spec (reference)

> Source: Miinto Integration help, Product Data section. This is a condensed
> working reference — the live docs are authoritative:
> - Headers (column spec): https://miinto-integration.elevio.help/en/articles/3-product-feed-headers
> - All Product Data docs: https://miinto-integration.elevio.help/en/categories/1-product-data
> - FAS validator: https://proxy-fas.miinto.net/feed

## Format & delivery
- **TSV** (tab-separated) or CSV; extension `.tsv`/`.txt`/`.csv`. **UTF-8**, **Unix EOL**.
  Header row required; column names **case-sensitive**; order irrelevant.
- **Pull model:** Miinto **fetches the file every 30 minutes** from your URL. **Fixed
  filename** (no date/time). **Full feed every time — no delta.** Download < 15s,
  first byte < 5s.
- **Hosting:** HTTP/HTTPS or FTP, externally reachable; auth = **HTTP Basic Auth or
  FTP credentials only (no sFTP)**.
- **Images:** **JPG or WEBP only**; server cert from a trusted CA (no `http://`); URLs
  stable once live; no user-agent required; **percent-encode** special chars in URLs.

## Validation
- **FAS (Feed Analysis Service):** `https://proxy-fas.miinto.net/feed` — free, **no
  login**. Enter your **feed URL** + feed type `shop`, click Analyze. Must pass with
  **no blocking errors**. Manual: `http://files.miinto.com/sample/Miinto_FAS_manual_v1.0.pdf`.

## Data model
- **One row per variant.** Variants of one product share `item_group_id`; each row
  keeps its own unique `id`. All variants of a product must be in the same feed.
- **Uniqueness key:** `item_group_id` + `size` + `color` + `brand` must be unique —
  duplicates are rejected.
- **Immutable once live:** `item_group_id`, `brand`, `color`, `size` — changing them
  takes products offline (manual removal by Miinto). **Only stock + retail price +
  discount price auto-update**; any other change requires removing & re-sending.

## Mandatory attributes
| Column | Constraint |
|---|---|
| `id` | string; unique SKU; stable across updates |
| `item_group_id` | string; shared across a product's variants |
| `c:style_id:string` | designer/style id; unique per model+colour |
| `brand` | ≤149 chars |
| `title` | **must not contain brand, size, colour or id**; style + attributes + category |
| `color` | ≤254; brand's original colour; `Black/white`, `Multi-colour` |
| `size` | ≤254; brand-label size, no merchant conversion |
| `image_link` | JPG/WEBP; main image; stable URL; URL-encoded; first = white-bg packshot |
| `c:stock_level:integer` | non-negative int; set `0` (don't remove) when OOS, keep ≥1h |
| `c:retail_price_<CUR>:integer` | one per currency; **integer cents** (`100099`=1000.99); incl. VAT; **empty (not 0)** if none |
| `c:discount_retail_price_<CUR>:integer` | same encoding; price after discount |
| `material` | JSON per language: `{"en_EN.utf8":"…","da_DK.utf8":"…"}` |
| `madein` | ISO 3166-1 alpha-2 (e.g. `IT`); mandatory for non-EU sales |
| `description` | multiline wrapped in `"`; narrative + measurements |

## Optional attributes (ALL required in our feed)
| Column | Constraint |
|---|---|
| `gtin` | 9–13 digits (not the primary key); empty if absent |
| `c:title_<lang>:string` | translated title; no brand/size/id |
| `product_type` | category tree string, e.g. `Shoes > Sneakers` |
| `gender` | `M`/`F`/`U` (no kids — use `product_type` or `KIDS` prefix) |
| `additional_image_link` | comma-separated, **JPG only**, percent-encoded |
| `c:season_tag:string` | ≤8 chars, season code + year |
| `c:description_<lang>:string` | translated description; `"`-quoted |
| `washing` | JSON per language |
| `hs_code` | 6/8/10-digit HS code with dots (customs; non-EU) |

Languages: **DA/SV/NL/NO/EN/DE/PL/IT/FR/ES/FI**. Currencies: ISO 4217 (e.g. EUR, DKK, SEK).
