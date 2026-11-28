# Changelog

## 0.1.3 — 2026-11-28

Added an optional Ollama adapter that appends local-model notes while validating every cited review ID.

## 0.1.2 — 2026-11-25

- `convert` auto-detects the vendor (`google-maps`, `play-store`, `amazon`) from the CSV headers when
  `--source` is omitted and marks it `(auto-detected)` in its output; headers that match no vendor, only
  generic columns, or two vendors equally exit 1 and ask for `--source`. An explicit `--source` still
  overrides detection. `convert_file` now returns `(count, source)`.

## 0.1.1 — 2026-11-25

- Added `review-analysis convert`: turns Google Maps, Play Store and Amazon review exports (CSV)
  into the canonical `id,rating,text` CSV, tagging every row with its source and mapping vendor
  column names case-insensitively (Amazon text falls back to the headline when a row has no body).

## 0.1.0 — 2026-10-30

Initial release.
