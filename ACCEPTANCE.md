# Acceptance Criteria (Definition of Done)

The deliverable is accepted when **all** of the following hold:

## Output correctness
- [ ] Generates from the sample data in a **single command**, no errors.
- [ ] Output is **TSV, UTF-8, Unix (`\n`) line endings**, with a header row.
- [ ] Column names are **case-sensitive** and exact (match `docs/miinto-feed-spec.md`).
- [ ] **All** mandatory **and** optional columns are present in the header.
- [ ] **Dynamic columns** are generated from config:
      `c:retail_price_<CUR>:integer`, `c:discount_retail_price_<CUR>:integer`,
      `c:title_<lang>:string`, `c:description_<lang>:string`.
- [ ] Prices are **integer cents** (`1000.99` → `100099`); absent prices are
      **empty, not `0`**.
- [ ] **One row per variant**; variants of a product share the same `item_group_id`.
- [ ] Multiline descriptions are correctly **quoted**; image URLs are **percent-encoded**.
- [ ] Optional values are left **blank** where source data is absent.

## Validation
- [ ] Passes **FAS** (`https://proxy-fas.miinto.net/feed`, type `shop`) with **no
      blocking errors**.
- [ ] Output **structure + stable fields** match the reference (per matched variant id). Prices, **c:stock_level**, and description whitespace may differ (the reference is a point-in-time snapshot).

## Config-driven
- [ ] Adding a currency or language is a **config change only** — no code edits.

## Engineering
- [ ] Unit tests cover: price→cents (incl. whole numbers, missing→empty, no zero),
      dynamic currency/language column generation, header ordering, variant grouping
      (correct row count + shared fields), multiline quoting, URL percent-encoding,
      output structure (TSV / Unix EOL).
- [ ] Clean, documented code; README explains how to run.
- [ ] Delivered via Pull Request(s) in this repo.

## Hosting
- [ ] Generated feed is served at a reachable HTTPS URL that **validates in FAS**.
      (FAS has no auth field — host **without** Basic Auth for the trial. Basic Auth
      is Miinto's production pull requirement, handled on our side.)

> "Passes FAS with no blocking errors on the sample data" is part of the deliverable —
> the revision cycles needed to reach a clean FAS pass are included in the fixed price.
