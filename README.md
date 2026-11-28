# review-analysis

[![tests](https://github.com/Ravishankerchaturvedi/review-analysis/actions/workflows/tests.yml/badge.svg)](https://github.com/Ravishankerchaturvedi/review-analysis/actions/workflows/tests.yml)
![python](https://img.shields.io/badge/python-3.10%2B-blue)
![license](https://img.shields.io/badge/license-MIT-green)
![dependencies](https://img.shields.io/badge/dependencies-none-brightgreen)

**Customer review analysis you can check.** Reviews in (CSV or JSON from Google, Amazon, app stores or your own
forms, with built-in converters for Google Maps, Play Store and Amazon exports), a report out (Markdown + JSON):
themes, sentiment split, top complaints and praise, each citing the review IDs behind it, plus draft replies marked
for a human to approve.

A runnable starter agent: deterministic by default, no API key needed, with an optional Ollama adapter for local-model notes.

## Problem

Review piles are too large to read by hand, and summaries without citations cannot be checked. This starter aggregates reviews into themes, sentiment and draft replies while citing the real review IDs behind every finding, so a human can verify each claim.

## Install

```bash
pip install -e .[test]
```

## Quickstart

```bash
review-analysis analyze examples/sample_reviews.csv --out-md report.md --out-json report.json
cat report.md
```

Real output of the quickstart above (run on 2026-11-28):

```
# Review Analysis Report

## Summary

- Total reviews: 30
- Positive: 15
- Neutral: 3
- Negative: 12

## Themes

- **delivery** (7): r002, r007, r013, r016, r023, r025, r028
- **product_quality** (8): r001, r005, r012, r015, r018, r023, r027, r030
- **customer_service** (7): r004, r010, r013, r017, r020, r026, r029
- **price** (10): r001, r006, r012, r015, r016, r019, r022, r027, r029, r030
- **usability** (6): r003, r008, r011, r014, r021, r024

## Top complaints

- **customer_service** (4): r004, r013, r017, r029
- **delivery** (4): r002, r013, r023, r025
- **price** (3): r006, r015, r029
- **usability** (3): r008, r011, r021
- **product_quality** (2): r015, r023

## Top praise

- **price** (5): r001, r012, r016, r022, r030
- **product_quality** (5): r001, r005, r012, r018, r030
- **customer_service** (3): r010, r020, r026
- **delivery** (3): r007, r016, r028
- **usability** (3): r003, r014, r024

## Draft replies (for human approval)

- customer_service: DRAFT (for human approval): We apologize for the support delay. We are reviewing your case and will follow up shortly.
- delivery: DRAFT (for human approval): We are sorry about the delivery issue. Could you share your order number so we can investigate the shipment?
- price: DRAFT (for human approval): Thank you for the feedback on pricing. We are reviewing our value proposition.
- usability: DRAFT (for human approval): We are sorry setup was difficult. We will improve our instructions and guides.
- product_quality: DRAFT (for human approval): We are sorry the product did not meet expectations. Please share details and photos so we can arrange a replacement or refund.
```

## Convert vendor exports

Vendor review exports use their own column names. `convert` maps them onto the canonical
`id,rating,text` CSV (plus `author`,`date`,`source`), tagging every row with its source, so the
analyser can read the file straight away. The vendor is auto-detected from the headers when
`--source` is omitted; an explicit `--source` (one of `google-maps`, `play-store`, `amazon`)
always overrides detection:

```bash
review-analysis convert examples/sample_google_maps.csv --out maps_reviews.csv
review-analysis convert examples/sample_play_store.csv --out play_reviews.csv
review-analysis convert examples/sample_amazon.csv --out amazon_reviews.csv
head -3 maps_reviews.csv
```

Real output of the commands above (run on 2026-11-25):

```
converted 6 reviews from google-maps export (auto-detected) to maps_reviews.csv
converted 6 reviews from play-store export (auto-detected) to play_reviews.csv
converted 6 reviews from amazon export (auto-detected) to amazon_reviews.csv
id,rating,text,author,date,source
gm-001,5,Lovely coffee and friendly service. Easy to find with parking.,Anya,2026-11-18T10:15:00Z,google-maps
gm-002,2,Delivery through the app was slow and the tracking never updated.,Rahul,2026-11-18T12:40:00Z,google-maps
```

Then run the Quickstart `analyze` on the converted file. Accepted columns (matched case-insensitively,
with spaces or underscores; first match wins):

- `google-maps`: id from `review_id`, rating from `review_rating`, text from `review_text`, author from `author_title`, date from `review_datetime_utc`
- `play-store`: id from `review_id`, rating from `star_rating`, text from `review_text`, author from `author_name`, date from `review_submitted_date`
- `amazon`: id from `review_id`, rating from `star_rating`, text from `review_body` (falls back to `review_headline` when a row has no body), author from `author`, date from `review_date`

Each source also accepts generic fallbacks (`id`, `rating`, `text`, `author`, `date`), and missing id
or text columns stop the conversion with an error naming the columns it expected. Auto-detection
scores each vendor by its own column names and refuses to guess — headers that match no vendor,
only generic names, or two vendors equally exit 1 and ask for `--source`.

## How it works

`convert` maps vendor column names (Google Maps, Play Store, Amazon) onto the canonical fields, tags every row with its source and writes the CSV the analyser reads. `analyze` loads CSV or JSON reviews, normalises each review (id, rating, text), computes sentiment (rating-based or keyword fallback), groups reviews into themes by keyword, counts top complaints and praise by theme, and drafts one reply per complaint theme marked as a draft for human approval. Every theme, complaint and praise cites the real review IDs that support it.

## Configuration

CSV columns: `id,rating,text` (optional `author`,`date`,`source`).
JSON: a list of objects with the same fields, or `{"reviews": [...]}`.

Optional LLM step: off by default. Set `REVIEW_ANALYSIS_LLM=1` and provide your own adapter via `REVIEW_ANALYSIS_LLM_MODULE` (a Python module exposing `enhance(report, reviews)`). No key or provider is hard-coded. If unavailable, the deterministic baseline is used.

For a free local model, use the included Ollama adapter (Ollama must already be running and the model must be pulled):

```bash
REVIEW_ANALYSIS_LLM=1 \
REVIEW_ANALYSIS_LLM_MODULE=review_analysis.ollama \
REVIEW_ANALYSIS_OLLAMA_MODEL=llama3.2:latest \
review-analysis analyze examples/sample_reviews.csv --out-md report.md --out-json report.json
```

The adapter asks Ollama for short notes about the top complaints, then removes any review ID that was not present in the input before writing the report. The notes remain advisory and are rendered with their supporting IDs.

Real output of the adapter validation run (run on 2026-11-28, using a local HTTP test double with the same Ollama response shape):

```
## Local-model notes (cited, for human review)
- **delivery** (r002): Check dispatch tracking.
```

## Use it with AI agents

- Exit code `0` = report written; `1` = the input could not be read. `convert` uses the same codes:
  `0` = converted CSV written; `1` = unreadable input, an unknown `--source`, headers that cannot be
  attributed to one vendor, or rows missing id/text.
- Hand it a raw vendor export and it can convert first (`review-analysis convert in.csv --out reviews.csv` — the vendor
  is auto-detected from the headers; pass `--source` to override), then analyse; `convert` errors name the columns it
  expected, so an agent can fix the mapping itself.
- `report.json` is the machine-readable form: an agent can read the top complaints and their review IDs, then
  draft fixes or replies that a human approves.
- The repo ships a `SKILL.md`, so coding agents that read skills (for example Claude Code) can run the analysis on a
  review export themselves.

## Limits

- Baseline is keyword-based and deterministic; themes are coarse.
- Ollama is optional, local-only, and its notes are suggestions; the model can still be wrong.
- Vendor converters read CSV exports only; Google Takeout JSON and HTML scrapes are not supported yet.
- Synthetic sample data only (clearly labelled in the file).
- Draft replies are drafts; a human must approve before sending.

## About

Built by Ravi Shanker Chaturvedi at RAD Media, Mumbai. We build AI systems for growing businesses; this is one of
our starter agents. Questions, bugs or a custom build: open an issue.
