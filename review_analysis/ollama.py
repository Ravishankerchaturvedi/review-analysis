"""Optional Ollama adapter for cited, local-model review notes."""

import json
import os
from urllib.error import URLError
from urllib.request import Request, urlopen


def _prompt(report, reviews):
    evidence = [{"id": r["id"], "text": r["text"]} for r in reviews]
    return (
        "Return JSON only, with an array field named ai_notes. Create one short "
        "actionable note for each top complaint theme. Each item must have theme, "
        "note, and review_ids. review_ids must be copied from the evidence; never "
        "invent IDs. Do not include personal data.\n\n"
        + json.dumps({"complaints": report["top_complaints"], "evidence": evidence})
    )


def enhance(report, reviews):
    """Add local-model notes while retaining only evidence-backed review IDs."""
    host = os.environ.get("REVIEW_ANALYSIS_OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
    model = os.environ.get("REVIEW_ANALYSIS_OLLAMA_MODEL", "llama3.2:latest")
    timeout = float(os.environ.get("REVIEW_ANALYSIS_OLLAMA_TIMEOUT", "30"))
    payload = json.dumps({"model": model, "prompt": _prompt(report, reviews),
                          "stream": False, "format": "json"}).encode("utf-8")
    request = Request(host + "/api/generate", data=payload,
                      headers={"Content-Type": "application/json"})
    try:
        with urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (OSError, URLError, ValueError) as exc:
        raise RuntimeError("Ollama request failed: %s" % exc) from exc
    try:
        generated = body["response"]
        result = json.loads(generated) if isinstance(generated, str) else generated
        notes = result["ai_notes"]
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeError("Ollama returned invalid JSON") from exc
    valid_ids = {r["id"] for r in reviews}
    clean = []
    for item in notes:
        if not isinstance(item, dict) or not isinstance(item.get("review_ids"), list):
            continue
        ids = [str(rid) for rid in item["review_ids"] if str(rid) in valid_ids]
        if item.get("theme") and item.get("note") and ids:
            clean.append({"theme": str(item["theme"]), "note": str(item["note"]),
                          "review_ids": ids})
    enriched = dict(report)
    enriched["ai_notes"] = clean
    return enriched
