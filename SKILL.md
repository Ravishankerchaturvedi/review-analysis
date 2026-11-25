---
name: review-analysis
description: Turn a pile of customer reviews (CSV or JSON) into a checkable report - themes, sentiment, top complaints and praise, each citing the review IDs behind it, plus draft replies for a human to approve. Use when someone shares review exports and asks what customers are saying or what to fix.
---

# review-analysis

## When to use
- Someone shares reviews (Google, Amazon, app store, survey exports) and wants the themes or the top complaints.
- You need findings that can be checked against the original reviews.

## Steps
1. If the export uses vendor column names (Google Maps, Play Store, Amazon), convert first:
   `review-analysis convert <export.csv> --out reviews.csv`
   (the vendor is auto-detected from the headers; pass `--source google-maps|play-store|amazon` to override;
   columns matched case-insensitively).
   Exit code 0 = converted CSV written; 1 = unreadable input, unknown source, headers that cannot be
   attributed to one vendor, or rows missing id/text.
2. Run `review-analysis analyze <reviews.csv> --out-md report.md --out-json report.json`. Exit code 0 means the
   report was written; 1 means the input could not be read.
3. Read `report.json`. Quote findings only with their review IDs.
4. Treat every reply in the report as a DRAFT: a human approves it before anything is sent.

## Rules
- Never state a finding without the review IDs that support it.
- The baseline is keyword-based and deterministic; say so when the themes look coarse.
