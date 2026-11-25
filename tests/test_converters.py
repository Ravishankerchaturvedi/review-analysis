import csv
import json
import subprocess
import sys
from pathlib import Path

import pytest

from review_analysis import converters

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable

GOOGLE_MAPS_CSV = """review_id,author_title,review_rating,review_text,review_datetime_utc
gm-1,Riya,5,Great food and friendly service,2026-11-20T10:00:00Z
gm-2,Arjun,1,Delivery was late and the order arrived cold,2026-11-21T09:00:00Z
"""

PLAY_STORE_CSV = """Review ID,Author Name,Star Rating,Review Text,Review Submitted Date
ps-1,Sam,4,Easy setup but the price is high,2026-11-18
ps-2,Priya,2,App keeps crashing after the update,2026-11-19
"""

AMAZON_CSV = """review_id,star_rating,review_headline,review_body,review_date
am-1,5,Best purchase,Works exactly as described and arrived fast,2026-11-15
am-2,2,Broke quickly,,Stopped working within a week,2026-11-16
"""


def run(*args, cwd=ROOT):
    return subprocess.run([PY, "-m", "review_analysis", *args], cwd=str(cwd),
                          capture_output=True, text=True)


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.reader(f))


def test_convert_google_maps(tmp_path):
    src = tmp_path / "export.csv"
    src.write_text(GOOGLE_MAPS_CSV, encoding="utf-8")
    out = tmp_path / "converted.csv"
    r = run("convert", str(src), "--source", "google-maps", "--out", str(out))
    assert r.returncode == 0, (r.returncode, r.stdout, r.stderr)
    assert "converted 2 reviews from google-maps" in r.stdout
    rows = read_csv(out)
    assert rows[0] == ["id", "rating", "text", "author", "date", "source"]
    assert rows[1] == ["gm-1", "5", "Great food and friendly service", "Riya",
                       "2026-11-20T10:00:00Z", "google-maps"]
    assert rows[2][0] == "gm-2" and rows[2][2].startswith("Delivery was late")


def test_convert_play_store_normalises_headers(tmp_path):
    src = tmp_path / "export.csv"
    src.write_text(PLAY_STORE_CSV, encoding="utf-8")
    out = tmp_path / "converted.csv"
    r = run("convert", str(src), "--source", "play-store", "--out", str(out))
    assert r.returncode == 0, (r.returncode, r.stdout, r.stderr)
    rows = read_csv(out)
    assert rows[1] == ["ps-1", "4", "Easy setup but the price is high", "Sam",
                       "2026-11-18", "play-store"]
    assert rows[2][2] == "App keeps crashing after the update"


def test_convert_amazon_headline_fallback(tmp_path):
    src = tmp_path / "export.csv"
    src.write_text(AMAZON_CSV, encoding="utf-8")
    out = tmp_path / "converted.csv"
    r = run("convert", str(src), "--source", "amazon", "--out", str(out))
    assert r.returncode == 0, (r.returncode, r.stdout, r.stderr)
    rows = read_csv(out)
    # am-1 keeps its body; am-2 has an empty body so the headline is used
    assert rows[1][2] == "Works exactly as described and arrived fast"
    assert rows[2][2] == "Broke quickly"


def test_convert_rows_tags_source_and_keeps_rating():
    rows = [{"review_id": "g1", "review_rating": "3", "review_text": "Usability is confusing"},
            {"review_id": "g2", "review_rating": "", "review_text": "Wonderful"}]
    out = converters.convert_rows(rows, "google-maps", fieldnames=list(rows[0].keys()))
    assert out[0] == {"id": "g1", "rating": "3", "text": "Usability is confusing",
                      "author": "", "date": "", "source": "google-maps"}
    assert out[1]["rating"] == ""


def test_convert_unknown_source_fails(tmp_path):
    src = tmp_path / "export.csv"
    src.write_text(GOOGLE_MAPS_CSV, encoding="utf-8")
    r = run("convert", str(src), "--source", "goodreads", "--out", str(tmp_path / "o.csv"))
    assert r.returncode == 1
    assert "unknown source" in r.stderr


def test_convert_missing_id_column_fails(tmp_path):
    src = tmp_path / "export.csv"
    src.write_text("review_rating,review_text\n5,Great\n", encoding="utf-8")
    r = run("convert", str(src), "--source", "google-maps", "--out", str(tmp_path / "o.csv"))
    assert r.returncode == 1
    assert "no column for 'id'" in r.stderr


def test_convert_row_missing_text_fails(tmp_path):
    src = tmp_path / "export.csv"
    src.write_text("review_id,review_text\ngm-1,\n", encoding="utf-8")
    r = run("convert", str(src), "--source", "google-maps", "--out", str(tmp_path / "o.csv"))
    assert r.returncode == 1
    assert "missing text" in r.stderr


def test_convert_then_analyze_end_to_end(tmp_path):
    src = tmp_path / "export.csv"
    src.write_text(GOOGLE_MAPS_CSV, encoding="utf-8")
    converted = tmp_path / "converted.csv"
    assert run("convert", str(src), "--source", "google-maps",
               "--out", str(converted)).returncode == 0
    report = tmp_path / "report.json"
    r = run("analyze", str(converted), "--out-json", str(report))
    assert r.returncode == 0, (r.returncode, r.stdout, r.stderr)
    data = json.loads(report.read_text())
    assert data["total_reviews"] == 2
    themes = {t["theme"]: t["review_ids"] for t in data["themes"]}
    assert themes["delivery"] == ["gm-2"]
    for item in data["themes"]:
        for rid in item["review_ids"]:
            assert rid in ("gm-1", "gm-2")


def test_detect_source_from_sample_headers():
    cases = {"amazon": "amazon", "google_maps": "google-maps",
             "play_store": "play-store"}
    for stem, expected in cases.items():
        with open(ROOT / "examples" / ("sample_%s.csv" % stem),
                  newline="", encoding="utf-8-sig") as f:
            headers = next(csv.reader(f))
        assert converters.detect_source(headers) == expected, stem


def test_detect_source_generic_headers_fail():
    with pytest.raises(ValueError, match="could not detect"):
        converters.detect_source(["id", "rating", "text"])


def test_convert_file_autodetects_and_returns_source(tmp_path):
    src = tmp_path / "export.csv"
    src.write_text(PLAY_STORE_CSV, encoding="utf-8")
    out = tmp_path / "converted.csv"
    n, source = converters.convert_file(src, None, out)
    assert (n, source) == (2, "play-store")
    assert read_csv(out)[1][5] == "play-store"


def test_convert_autodetects_on_cli(tmp_path):
    src = tmp_path / "export.csv"
    src.write_text(GOOGLE_MAPS_CSV, encoding="utf-8")
    out = tmp_path / "converted.csv"
    r = run("convert", str(src), "--out", str(out))
    assert r.returncode == 0, (r.returncode, r.stdout, r.stderr)
    assert "converted 2 reviews from google-maps export (auto-detected)" in r.stdout
    assert read_csv(out)[1][5] == "google-maps"


def test_convert_autodetect_ambiguous_fails_on_cli(tmp_path):
    src = tmp_path / "export.csv"
    src.write_text("id,rating,text\ng1,5,Great\n", encoding="utf-8")
    r = run("convert", str(src), "--out", str(tmp_path / "o.csv"))
    assert r.returncode == 1
    assert "could not detect" in r.stderr


def test_convert_explicit_source_overrides_detection(tmp_path):
    src = tmp_path / "export.csv"
    src.write_text(PLAY_STORE_CSV, encoding="utf-8")
    out = tmp_path / "converted.csv"
    r = run("convert", str(src), "--source", "google-maps", "--out", str(out))
    assert r.returncode == 0, (r.returncode, r.stdout, r.stderr)
    assert "(auto-detected)" not in r.stdout
    rows = read_csv(out)
    assert rows[1][5] == "google-maps"
    assert rows[1][1] == ""  # star_rating is not a google-maps rating column
