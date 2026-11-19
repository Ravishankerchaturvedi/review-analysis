# review-analysis

[![tests](https://github.com/Ravishankerchaturvedi/review-analysis/actions/workflows/tests.yml/badge.svg)](https://github.com/Ravishankerchaturvedi/review-analysis/actions/workflows/tests.yml)
![python](https://img.shields.io/badge/python-3.10%2B-blue)
![license](https://img.shields.io/badge/license-MIT-green)
![dependencies](https://img.shields.io/badge/dependencies-none-brightgreen)

**Customer review analysis you can check.** Reviews in (CSV or JSON from Google, Amazon, app stores or your own
forms), a report out (Markdown + JSON): themes, sentiment split, top complaints and praise, each citing the review
IDs behind it, plus draft replies marked for a human to approve.

A runnable starter agent: deterministic by default, no API key needed, with an optional hook for your own LLM.

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

Real output of the quickstart above (run on 2026-10-30):

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

## How it works

Loads CSV or JSON reviews, normalises each review (id, rating, text), computes sentiment (rating-based or keyword fallback), groups reviews into themes by keyword, counts top complaints and praise by theme, and drafts one reply per complaint theme marked as a draft for human approval. Every theme, complaint and praise cites the real review IDs that support it.

## Configuration

CSV columns: `id,rating,text` (optional `author`,`date`,`source`).
JSON: a list of objects with the same fields, or `{"reviews": [...]}`.

Optional LLM step: off by default. Set `REVIEW_ANALYSIS_LLM=1` and provide your own adapter via `REVIEW_ANALYSIS_LLM_MODULE` (a Python module exposing `enhance(report, reviews)`). No key or provider is hard-coded. If unavailable, the deterministic baseline is used.

## Use it with AI agents

- Exit code `0` = report written; `1` = the input could not be read.
- `report.json` is the machine-readable form: an agent can read the top complaints and their review IDs, then
  draft fixes or replies that a human approves.
- The repo ships a `SKILL.md`, so coding agents that read skills (for example Claude Code) can run the analysis on a
  review export themselves.

## Limits

- Baseline is keyword-based and deterministic; themes are coarse.
- Synthetic sample data only (clearly labelled in the file).
- Draft replies are drafts; a human must approve before sending.

## About

Built by Ravi Shanker Chaturvedi at RAD Media, Mumbai. We build AI systems for growing businesses; this is one of
our starter agents. Questions, bugs or a custom build: open an issue.