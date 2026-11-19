import csv
import json
import os
from pathlib import Path

THEMES = {
    "delivery": ["shipping", "delivery", "delivered", "arrived", "package", "tracking"],
    "product_quality": ["quality", "broken", "defect", "durable", "material", "build", "flimsy"],
    "customer_service": ["support", "service", "help", "response", "refund", "agent"],
    "price": ["price", "cost", "expensive", "cheap", "value", "money", "costly"],
    "usability": ["easy", "hard", "use", "interface", "setup", "intuitive", "confusing"],
}

DRAFT_REPLIES = {
    "delivery": "DRAFT (for human approval): We are sorry about the delivery issue. "
                "Could you share your order number so we can investigate the shipment?",
    "product_quality": "DRAFT (for human approval): We are sorry the product did not meet "
                       "expectations. Please share details and photos so we can arrange a "
                       "replacement or refund.",
    "customer_service": "DRAFT (for human approval): We apologize for the support delay. "
                        "We are reviewing your case and will follow up shortly.",
    "price": "DRAFT (for human approval): Thank you for the feedback on pricing. We are "
             "reviewing our value proposition.",
    "usability": "DRAFT (for human approval): We are sorry setup was difficult. We will "
                 "improve our instructions and guides.",
}


def load_reviews(path):
    p = Path(path)
    if not p.is_file():
        raise ValueError("input file not found: %s" % path)
    if p.stat().st_size == 0:
        raise ValueError("input file is empty")
    text = p.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError("input file is empty")
    # JSON
    if p.suffix.lower() == ".json":
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            raise ValueError("malformed JSON: %s" % e)
        if isinstance(data, dict):
            reviews = data.get("reviews", [])
        elif isinstance(data, list):
            reviews = data
        else:
            raise ValueError("JSON must be a list or an object with 'reviews'")
    else:
        # CSV
        if text.count('"') % 2 != 0:
            raise ValueError("malformed CSV: unmatched quote")
        try:
            with open(p, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                if reader.fieldnames is None:
                    raise ValueError("CSV has no header row")
                reviews = list(reader)
        except csv.Error as e:
            raise ValueError("malformed CSV: %s" % e)
    if not isinstance(reviews, list) or len(reviews) == 0:
        raise ValueError("no reviews found in input")
    # normalize
    out = []
    for i, r in enumerate(reviews):
        if not isinstance(r, dict):
            raise ValueError("review %d is not an object" % i)
        rid = r.get("id") or r.get("review_id") or r.get("ID")
        if rid is None or str(rid).strip() == "":
            raise ValueError("review %d missing id" % i)
        rating_raw = r.get("rating") or r.get("stars") or r.get("score")
        try:
            rating = int(float(rating_raw)) if rating_raw is not None else None
        except (TypeError, ValueError):
            rating = None
        txt = r.get("text") or r.get("review") or r.get("body") or r.get("content")
        if txt is None or str(txt).strip() == "":
            raise ValueError("review %s missing text" % rid)
        out.append({
            "id": str(rid).strip(),
            "rating": rating,
            "text": str(txt).strip(),
        })
    # duplicate id check
    ids = [r["id"] for r in out]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate review ids in input")
    return out


def sentiment_of(review):
    rating = review.get("rating")
    if rating is not None:
        if rating >= 4:
            return "positive"
        if rating <= 2:
            return "negative"
        return "neutral"
    text = review["text"].lower()
    pos_words = ["great", "good", "excellent", "love", "fast", "helpful", "easy"]
    neg_words = ["bad", "poor", "slow", "broken", "terrible", "hard", "confusing"]
    p = sum(1 for w in pos_words if w in text)
    n = sum(1 for w in neg_words if w in text)
    if p > n:
        return "positive"
    if n > p:
        return "negative"
    return "neutral"


def themes_for(review):
    text = review["text"].lower()
    found = []
    for theme, keywords in THEMES.items():
        if any(kw in text for kw in keywords):
            found.append(theme)
    return found


def analyze(reviews):
    reviews = list(reviews)
    if not reviews:
        raise ValueError("no reviews to analyze")
    sentiment_counts = {"positive": 0, "neutral": 0, "negative": 0}
    theme_reviews = {t: [] for t in THEMES}
    complaint_themes = {t: [] for t in THEMES}
    praise_themes = {t: [] for t in THEMES}
    for r in reviews:
        s = sentiment_of(r)
        sentiment_counts[s] += 1
        ts = themes_for(r)
        for t in ts:
            theme_reviews[t].append(r["id"])
            if s == "negative":
                complaint_themes[t].append(r["id"])
            elif s == "positive":
                praise_themes[t].append(r["id"])

    themes = []
    for t in THEMES:
        ids = theme_reviews[t]
        if ids:
            themes.append({"theme": t, "count": len(ids), "review_ids": ids})

    top_complaints = []
    for t in THEMES:
        ids = complaint_themes[t]
        if ids:
            top_complaints.append({"theme": t, "count": len(ids), "review_ids": ids})
    top_complaints.sort(key=lambda x: (-x["count"], x["theme"]))

    top_praise = []
    for t in THEMES:
        ids = praise_themes[t]
        if ids:
            top_praise.append({"theme": t, "count": len(ids), "review_ids": ids})
    top_praise.sort(key=lambda x: (-x["count"], x["theme"]))

    draft_replies = []
    for c in top_complaints:
        t = c["theme"]
        draft_replies.append({"theme": t, "draft": DRAFT_REPLIES.get(t, "DRAFT (for human approval): Thank you for your feedback.")})

    total = len(reviews)
    report = {
        "total_reviews": total,
        "sentiment_split": sentiment_counts,
        "themes": themes,
        "top_complaints": top_complaints,
        "top_praise": top_praise,
        "draft_replies": draft_replies,
    }

    # optional LLM step (off by default)
    if os.environ.get("REVIEW_ANALYSIS_LLM", "").strip().lower() in ("1", "true", "yes", "on"):
        module_name = os.environ.get("REVIEW_ANALYSIS_LLM_MODULE", "").strip()
        if module_name:
            try:
                import importlib
                mod = importlib.import_module(module_name)
                if hasattr(mod, "enhance"):
                    report = mod.enhance(report, reviews)
            except Exception:
                pass
    return report


def render_markdown(report):
    lines = []
    lines.append("# Review Analysis Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("- Total reviews: %d" % report["total_reviews"])
    ss = report["sentiment_split"]
    lines.append("- Positive: %d" % ss["positive"])
    lines.append("- Neutral: %d" % ss["neutral"])
    lines.append("- Negative: %d" % ss["negative"])
    lines.append("")
    lines.append("## Themes")
    lines.append("")
    for t in report["themes"]:
        lines.append("- **%s** (%d): %s" % (t["theme"], t["count"], ", ".join(t["review_ids"])))
    lines.append("")
    lines.append("## Top complaints")
    lines.append("")
    for c in report["top_complaints"]:
        lines.append("- **%s** (%d): %s" % (c["theme"], c["count"], ", ".join(c["review_ids"])))
    lines.append("")
    lines.append("## Top praise")
    lines.append("")
    for p in report["top_praise"]:
        lines.append("- **%s** (%d): %s" % (p["theme"], p["count"], ", ".join(p["review_ids"])))
    lines.append("")
    lines.append("## Draft replies (for human approval)")
    lines.append("")
    for d in report["draft_replies"]:
        lines.append("- %s: %s" % (d["theme"], d["draft"]))
    lines.append("")
    return "\n".join(lines)