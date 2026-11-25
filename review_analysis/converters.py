"""Convert vendor review exports (CSV) into the canonical review CSV format.

Supported sources: google-maps, play-store, amazon. Each source maps that
vendor's column names (case-insensitive, with spaces or underscores) onto the
canonical id, rating, text fields plus optional author and date, and tags
every row with its source so reviews from several exports can be combined.
The vendor can also be detected from the headers alone: see detect_source().
"""

import csv
import io
from pathlib import Path

CANONICAL_COLUMNS = ["id", "rating", "text", "author", "date", "source"]

# One alias list per canonical field, ordered most- to least-specific.
# Headers are matched after normalising: lowercase, trimmed, spaces -> underscores.
FIELD_ALIASES = {
    "google-maps": {
        "id": ["review_id", "reviewid", "id"],
        "rating": ["review_rating", "rating", "stars"],
        "text": ["review_text", "text", "comment"],
        "author": ["author_title", "author", "reviewer"],
        "date": ["review_datetime_utc", "date", "published_at"],
    },
    "play-store": {
        "id": ["review_id", "reviewid", "id"],
        "rating": ["star_rating", "rating", "stars"],
        "text": ["review_text", "text", "content", "review"],
        "author": ["author_name", "author", "reviewer"],
        "date": ["review_submitted_date", "review_last_updated_date", "date"],
    },
    "amazon": {
        "id": ["review_id", "reviewid", "id"],
        "rating": ["star_rating", "rating", "stars"],
        "text": ["review_body", "body", "text", "content"],
        "author": ["author", "reviewer"],
        "date": ["review_date", "date"],
    },
}

# If the text column is empty row-by-row, fall back to the headline column.
HEADLINE_FALLBACK = {
    "amazon": ["review_headline", "review_title", "headline", "title"],
}


def _norm(header):
    return header.replace("\ufeff", "").strip().lower().replace(" ", "_")


def _pick_column(aliases, norm_map):
    for alias in aliases:
        if alias in norm_map:
            return norm_map[alias]
    return None


def _cell(row, column):
    if column is None:
        return ""
    value = row.get(column)
    if value is None:
        return ""
    return str(value).strip()


def detect_source(fieldnames):
    """Attribute a vendor export to its source from the CSV headers alone.

    Every source that can supply the required id and text fields is scored by
    how many of its most-specific column aliases the headers contain; a strict
    winner is returned. Raises ValueError when no source matches, when only
    generic column names are present, or when several sources match equally
    well (pass --source explicitly in those cases).
    """
    norm_map = {_norm(h): h for h in (fieldnames or [])}
    scores = {}
    for source, aliases in FIELD_ALIASES.items():
        columns = {field: _pick_column(names, norm_map)
                   for field, names in aliases.items()}
        if columns["id"] is None or columns["text"] is None:
            continue
        scores[source] = sum(
            1 for field, names in aliases.items()
            if names and columns[field] is not None
            and _norm(columns[field]) == names[0]
        )
    if not scores:
        raise ValueError(
            "could not detect the export source from the headers (no source "
            "supplies id and text); pass --source (one of: %s)"
            % ", ".join(sorted(FIELD_ALIASES))
        )
    best = max(scores.values())
    if best < 1:
        raise ValueError(
            "could not detect the export source from the headers (only "
            "generic column names found); pass --source (one of: %s)"
            % ", ".join(sorted(FIELD_ALIASES))
        )
    winners = sorted(s for s, n in scores.items() if n == best)
    if len(winners) > 1:
        raise ValueError(
            "could not detect the export source from the headers: matches %s "
            "equally well; pass --source to choose" % " and ".join(winners)
        )
    return winners[0]


def convert_rows(rows, source, fieldnames=None):
    """Convert raw CSV rows from a vendor export into canonical review dicts."""
    if source not in FIELD_ALIASES:
        raise ValueError(
            "unknown source '%s' (expected one of: %s)"
            % (source, ", ".join(sorted(FIELD_ALIASES)))
        )
    aliases = FIELD_ALIASES[source]
    headers = list(fieldnames) if fieldnames else (list(rows[0].keys()) if rows else [])
    norm_map = {_norm(h): h for h in headers}
    columns = {}
    for field in ("id", "text", "rating", "author", "date"):
        column = _pick_column(aliases[field], norm_map)
        if field in ("id", "text") and column is None:
            raise ValueError(
                "unrecognised %s export: no column for '%s' (expected one of: %s)"
                % (source, field, ", ".join(aliases[field]))
            )
        columns[field] = column
    headline_column = _pick_column(HEADLINE_FALLBACK.get(source, []), norm_map)

    out = []
    for i, row in enumerate(rows, start=2):
        text = _cell(row, columns["text"])
        if not text:
            text = _cell(row, headline_column)
        rec = {
            "id": _cell(row, columns["id"]),
            "rating": _cell(row, columns["rating"]),
            "text": text,
            "author": _cell(row, columns["author"]),
            "date": _cell(row, columns["date"]),
            "source": source,
        }
        if not rec["id"]:
            raise ValueError("row %d missing id" % i)
        if not rec["text"]:
            raise ValueError("row %d missing text" % i)
        out.append(rec)
    return out


def convert_file(input_path, source, output_path):
    """Convert a vendor export CSV at input_path into a canonical CSV at output_path.

    source may be a known source name, or None/"auto" to detect the vendor
    from the CSV headers. Returns (count, source): the number of reviews
    converted and the source actually used. Raises ValueError on an unknown
    source, an unreadable input, rows missing id or text, or headers that
    cannot be attributed to one source when detecting.
    """
    if source not in (None, "auto") and source not in FIELD_ALIASES:
        raise ValueError(
            "unknown source '%s' (expected one of: %s)"
            % (source, ", ".join(sorted(FIELD_ALIASES)))
        )
    p = Path(input_path)
    if not p.is_file():
        raise ValueError("input file not found: %s" % input_path)
    text = p.read_text(encoding="utf-8-sig")
    if not text.strip():
        raise ValueError("input file is empty")
    if text.count('"') % 2 != 0:
        raise ValueError("malformed CSV: unmatched quote")
    try:
        reader = csv.DictReader(io.StringIO(text))
        fieldnames = reader.fieldnames
        if fieldnames is None:
            raise ValueError("CSV has no header row")
        rows = list(reader)
    except csv.Error as e:
        raise ValueError("malformed CSV: %s" % e)
    if not rows:
        raise ValueError("no reviews found in input")
    if source in (None, "auto"):
        source = detect_source(fieldnames)
    converted = convert_rows(rows, source, fieldnames=fieldnames)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(CANONICAL_COLUMNS)
        for rec in converted:
            writer.writerow([rec[c] for c in CANONICAL_COLUMNS])
    return len(converted), source
