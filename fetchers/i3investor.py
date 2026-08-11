import json
import re
from datetime import datetime, timedelta, timezone

import requests

_I3_BASE = "https://klse.i3investor.com"
_I3_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

_ANNOUNCEMENT_LINK_RE = re.compile(r"href=['\"]([^'\"]+)['\"][^>]*>([^<]+)<")


def _fetch_i3investor_targets(klse_code: str, limit: int = 5) -> list:
    url = f"{_I3_BASE}/web/stock/analysis-price-target/{klse_code}"
    try:
        r = requests.get(url, headers=_I3_HEADERS, timeout=15)
        r.raise_for_status()
    except Exception:
        return []

    match = re.search(r"var dtdata\s*=\s*(\[.*?\]);", r.text, re.DOTALL)
    if not match:
        return []
    try:
        rows = json.loads(match.group(1))
    except Exception:
        return []

    results = []
    for row in rows[:limit]:
        research_path = row[7] if len(row) > 7 else ""
        results.append({
            "date":       row[0],
            "open_price": row[1],
            "target":     row[2],
            "upside":     row[3],
            "call":       row[4],
            "firm":       row[5],
            "url":        (_I3_BASE + research_path) if research_path else "",
        })
    return results


def _fetch_i3investor_announcements(klse_code: str, days: int = 7) -> list:
    url = f"{_I3_BASE}/web/stock/announcement/{klse_code}"
    try:
        r = requests.get(url, headers=_I3_HEADERS, timeout=15)
        r.raise_for_status()
    except Exception:
        return []

    match = re.search(r"(?:var|const)\s+dtdata\s*=\s*(\[.*?\]);", r.text, re.DOTALL)
    if not match:
        return []
    try:
        rows = json.loads(match.group(1))
    except Exception:
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    results = []
    for row in rows:
        if len(row) < 2:
            continue
        date_str, link_html = row[0], row[1]
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if dt < cutoff:
            continue

        link_match = _ANNOUNCEMENT_LINK_RE.search(link_html)
        if not link_match:
            continue
        href, title = link_match.group(1), link_match.group(2).strip()
        results.append({
            "_dt": dt,
            "date": dt.strftime("%-d %b %Y"),
            "title": title,
            "url": (_I3_BASE + href) if href.startswith("/") else href,
        })

    results.sort(key=lambda a: a["_dt"], reverse=True)
    for a in results:
        a.pop("_dt", None)
    return results
