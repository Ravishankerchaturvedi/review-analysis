import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
SAMPLE = ROOT / "examples" / "sample_reviews.csv"


def run(*args, cwd=ROOT):
    return subprocess.run([PY, "-m", "review_analysis", *args], cwd=str(cwd),
                         capture_output=True, text=True)


def test_sample_report_themes():
    out_md = ROOT / "tests" / "_report.md"
    out_json = ROOT / "tests" / "_report.json"
    for p in (out_md, out_json):
        if p.exists():
            p.unlink()
    r = run("analyze", str(SAMPLE), "--out-md", str(out_md), "--out-json", str(out_json))
    assert r.returncode == 0, (r.returncode, r.stdout, r.stderr)
    data = json.loads(out_json.read_text())
    theme_names = {t["theme"] for t in data["themes"]}
    assert "delivery" in theme_names
    assert "product_quality" in theme_names
    assert "price" in theme_names
    # cleanup
    for p in (out_md, out_json):
        if p.exists():
            p.unlink()


def test_findings_cite_real_ids():
    import csv
    with open(SAMPLE, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    valid_ids = {r["id"] for r in rows}
    out_json = ROOT / "tests" / "_report2.json"
    if out_json.exists():
        out_json.unlink()
    run("analyze", str(SAMPLE), "--out-json", str(out_json))
    data = json.loads(out_json.read_text())
    for section in ("themes", "top_complaints", "top_praise"):
        for item in data[section]:
            for rid in item["review_ids"]:
                assert rid in valid_ids
    out_json.unlink()


def test_drafts_marked():
    out_md = ROOT / "tests" / "_report3.md"
    if out_md.exists():
        out_md.unlink()
    run("analyze", str(SAMPLE), "--out-md", str(out_md))
    text = out_md.read_text()
    assert "DRAFT" in text
    assert "human approval" in text
    out_md.unlink()


def test_empty_input_fails(tmp_path):
    p = tmp_path / "empty.csv"
    p.write_text("", encoding="utf-8")
    r = run("analyze", str(p))
    assert r.returncode == 1


def test_malformed_input_fails(tmp_path):
    p = tmp_path / "bad.csv"
    p.write_text("id,rating,text\n1,5,\"unterminated\n", encoding="utf-8")
    r = run("analyze", str(p))
    assert r.returncode == 1


def test_empty_reviews_json_fails(tmp_path):
    p = tmp_path / "empty.json"
    p.write_text("[]", encoding="utf-8")
    r = run("analyze", str(p))
    assert r.returncode == 1


def test_json_input_works(tmp_path):
    p = tmp_path / "in.json"
    p.write_text(json.dumps([
        {"id": "a", "rating": 5, "text": "great value and quality"},
        {"id": "b", "rating": 1, "text": "shipping was slow"},
    ]), encoding="utf-8")
    out_json = tmp_path / "out.json"
    r = run("analyze", str(p), "--out-json", str(out_json))
    assert r.returncode == 0
    data = json.loads(out_json.read_text())
    assert data["total_reviews"] == 2


def test_ollama_adapter_keeps_only_real_review_ids(monkeypatch):
    from review_analysis import ollama

    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self):
            return json.dumps({"response": json.dumps({"ai_notes": [
                {"theme": "delivery", "note": "Check dispatch tracking.",
                 "review_ids": ["r002", "made-up-id"]},
            ]})}).encode("utf-8")

    monkeypatch.setattr(ollama, "urlopen", lambda *args, **kwargs: Response())
    report = {"top_complaints": [{"theme": "delivery", "review_ids": ["r002"]}]}
    enriched = ollama.enhance(report, [{"id": "r002", "text": "late delivery"}])
    assert enriched["ai_notes"] == [{"theme": "delivery", "note": "Check dispatch tracking.",
                                      "review_ids": ["r002"]}]
