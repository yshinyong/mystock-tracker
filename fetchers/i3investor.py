import json
import re

import requests

_I3_BASE = "https://klse.i3investor.com"
_I3_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


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
