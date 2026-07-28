from email.utils import parsedate_to_datetime

from .sentiment import score_sentiment


def _fmt_price(val) -> str:
    if val is None:
        return "N/A"
    try:
        return f"{float(val):.3f}"
    except (TypeError, ValueError):
        return "N/A"


def _pct_diff(current, reference, label: str) -> str:
    try:
        diff = ((float(current) - float(reference)) / float(reference)) * 100
        sign = "+" if diff >= 0 else ""
        return f"{sign}{diff:.1f}% vs {label}"
    except (TypeError, ValueError, ZeroDivisionError):
        return "N/A"


def _parse_rss_datetime(entry):
    for field in ("published", "updated"):
        raw = entry.get(field, "")
        if raw:
            try:
                return parsedate_to_datetime(raw)
            except Exception:
                pass
    return None


def _format_date(dt) -> str:
    return dt.strftime("%-d %b %Y") if dt else "N/A"


def _make_news_item(title, link, source, dt):
    return {
        "title": title,
        "sentiment": score_sentiment(title),
        "link": link,
        "source": source,
        "date": _format_date(dt),
        "_dt": dt,
    }
