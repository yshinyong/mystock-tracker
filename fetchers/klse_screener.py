from datetime import datetime, timedelta, timezone

import requests
from bs4 import BeautifulSoup

_KLSE_SCREENER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def _fetch_klse_comments(klse_code: str, days: int = 7) -> list:
    url = f"https://www.klsescreener.com/v2/comments/all/stock/{klse_code}"
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    try:
        r = requests.get(url, headers=_KLSE_SCREENER_HEADERS, timeout=15)
        r.raise_for_status()
    except Exception:
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    top_comments = soup.find_all(
        "div",
        class_=lambda c: c and "cardmy" in c and "comment" in c and "ml-1" in c,
    )

    results = []
    for block in top_comments:
        dt_tag = block.find("a", attrs={"data-datetime": True})
        if not dt_tag:
            continue
        raw_dt = dt_tag["data-datetime"]
        try:
            # Format: "2026-05-07 21:01:36 +0800"
            dt = datetime.strptime(raw_dt, "%Y-%m-%d %H:%M:%S %z")
        except ValueError:
            continue
        if dt < cutoff:
            continue

        username_tag = block.find("strong", class_="text-primary")
        username = username_tag.get_text(strip=True) if username_tag else "Unknown"

        msg_tag = block.find("div", class_="message-container")
        message = msg_tag.get_text(strip=True) if msg_tag else ""
        if not message:
            continue

        likes_tag = block.find("span", attrs={"data-id": True})
        likes = 0
        if likes_tag:
            txt = likes_tag.get_text(strip=True)
            try:
                likes = int(txt.split()[0])
            except (ValueError, IndexError):
                likes = 0

        results.append({
            "username": username,
            "message": message,
            "date": dt.strftime("%-d %b %Y %H:%M"),
            "likes": likes,
            "_dt": dt,
        })

    results.sort(key=lambda c: c["_dt"], reverse=True)
    for c in results:
        c.pop("_dt")
    return results
