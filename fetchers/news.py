from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import feedparser

from .formatting import _make_news_item, _parse_rss_datetime

_EDGE_MARKETS_RSS = "https://www.theedgemarkets.com/rss"
_STAR_BUSINESS_RSS = "https://www.thestar.com.my/rss/business/business-news"
_MALAYSIAN_RESERVE_RSS = "https://themalaysianreserve.com/feed/"
_NST_BUSINESS_RSS = "https://www.nst.com.my/business.rss"

# Verbs that, when following a broker name at the start of a headline, signal
# analyst/broker commentary (e.g. "Maybank Lifts Bursa Malaysia To Buy ...").
_BROKER_VERBS = (
    "lifts", "cuts", "raises", "lowers", "upgrades", "downgrades",
    "starts coverage on", "initiates coverage on", "initiates",
    "reiterates", "maintains buy on", "maintains sell on",
    "maintains hold on", "rates", "tags", "ups",
)

# Words that, after a broker verb, indicate the headline is about the
# broker's *own* company (e.g. "RHB lifts dividend guidance...") and not
# commentary on a different stock.
_OWN_COMPANY_FOLLOWUPS = (
    "dividend", "dividends", "interim", "final dividend",
    "fy", "1q", "2q", "3q", "4q", "q1", "q2", "q3", "q4",
    "profit", "net profit", "earnings", "revenue",
    "guidance", "outlook", "forecast", "rm",
)

# Market-roundup / multi-stock list headlines: even if they mention the stock,
# they are not specifically about that counter.
_MARKET_ROUNDUP_PHRASES = (
    "short interest weekly",
    "decliners dominate",
    "gainers dominate",
    "top movers",
    "top gainers",
    "top decliners",
    "top losers",
    "biggest gainers",
    "biggest losers",
    "bursa roundup",
    "market roundup",
    "market snapshot",
    "bursa snapshot",
    "lead losses",
    "lead gains",
    "lead the gains",
    "lead the losses",
    "leading the gains",
    "leading the losses",
)

_BROKER_REPORT_KEYWORDS = (
    "target price", "price target", " tp ", "tp:", "tp of", "tp to",
    "buy", "sell", "hold", "overweight", "underweight", "outperform",
    "underperform", "neutral", "upgrade", "downgrade", "initiate",
    "reiterate", "maintain",
)

_EXCLUDED_SOURCES = {"ad hoc news"}


def _is_about_stock(title: str, label: str, aliases: list, broker_aliases: list) -> bool:
    """Return True if the headline is genuinely about this stock counter.

    Filters out:
    - Headlines where the stock name does not appear in the title
    - Market roundups and multi-stock list headlines
    - Broker commentary patterns ("<broker> lifts/cuts/etc. <other company>")
    """
    if not title:
        return False
    title_lower = title.lower()
    company_names = [label.lower()] + [a.lower() for a in (aliases or [])]
    broker_names = [a.lower() for a in (broker_aliases or [])]

    if not any(name in title_lower for name in company_names):
        return False

    if any(phrase in title_lower for phrase in _MARKET_ROUNDUP_PHRASES):
        return False

    if ":" in title:
        after_colon = title.split(":", 1)[1]
        if after_colon.count(",") >= 2:
            return False

    # Broker-commentary detection: title starts with a broker name (either an
    # explicit broker alias or the company name itself acting as broker) +
    # broker verb + a target that is not the company's own metric.
    for broker_name in broker_names + company_names:
        prefix = broker_name + " "
        if not title_lower.startswith(prefix):
            continue
        rest = title_lower[len(prefix):].lstrip()
        for verb in _BROKER_VERBS:
            verb_token = verb + " "
            if not rest.startswith(verb_token):
                continue
            after_verb = rest[len(verb_token):].lstrip()
            if any(after_verb.startswith(name) for name in company_names):
                return True
            if any(after_verb.startswith(item) for item in _OWN_COMPANY_FOLLOWUPS):
                return True
            return False

    return True


def _is_recent(dt, max_age_days: int) -> bool:
    if dt is None:
        return False
    if max_age_days <= 0:
        return True
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    return dt >= cutoff


def _fetch_google_news(label: str, ticker: str, aliases: list) -> list:
    code = ticker.split(".")[0]
    queries = [
        f'"{label}" Bursa Malaysia',
        f'"{code}" {label} KLSE',
    ]
    for alias in (aliases or []):
        queries.append(f'"{alias}" Bursa Malaysia')

    seen = set()
    news = []
    for query in queries:
        url = f"https://news.google.com/rss/search?q={quote(query)}&hl=en-MY&gl=MY&ceid=MY:en"
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                title = entry.get("title", "")
                key = " ".join(title.lower().split())
                if not title or key in seen:
                    continue
                seen.add(key)
                news.append(_make_news_item(
                    title,
                    entry.get("link", "#"),
                    (entry.get("source") or {}).get("title", "Google News"),
                    _parse_rss_datetime(entry),
                ))
        except Exception:
            continue
    return news


def _fetch_yfinance_news(tk) -> list:
    try:
        raw = getattr(tk, "news", None) or []
        if isinstance(raw, dict):
            raw = list(raw.values())[0] if raw else []
        news = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            title = item.get("title", "")
            if not title:
                continue
            pub_ts = item.get("providerPublishTime")
            try:
                pub_dt = datetime.fromtimestamp(pub_ts, tz=timezone.utc) if pub_ts else None
            except Exception:
                pub_dt = None
            news.append(_make_news_item(
                title,
                item.get("link", "#"),
                item.get("publisher", "Yahoo Finance"),
                pub_dt,
            ))
        return news
    except Exception:
        return []


def _fetch_rss_filtered(url: str, source_name: str, label: str, aliases: list) -> list:
    try:
        feed = feedparser.parse(url)
        names = [label.lower()] + [a.lower() for a in (aliases or [])]
        news = []
        for entry in feed.entries:
            title = entry.get("title", "")
            summary = entry.get("summary", "")
            if not title:
                continue
            blob = (title + " " + summary).lower()
            if not any(name in blob for name in names):
                continue
            src = (entry.get("source") or {}).get("title", source_name)
            news.append(_make_news_item(title, entry.get("link", "#"), src, _parse_rss_datetime(entry)))
        return news
    except Exception:
        return []


def _deduplicate(news: list) -> list:
    seen = set()
    result = []
    for item in news:
        key = " ".join(item["title"].lower().split())
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def _is_broker_report(title: str) -> bool:
    t = title.lower()
    return any(kw in t for kw in _BROKER_REPORT_KEYWORDS)


def _fetch_all_news(tk, label: str, ticker: str, aliases: list, broker_aliases: list,
                    max_news: int, max_age_days: int) -> tuple:
    all_news = []
    all_news.extend(_fetch_yfinance_news(tk))
    all_news.extend(_fetch_google_news(label, ticker, aliases))
    all_news.extend(_fetch_rss_filtered(_EDGE_MARKETS_RSS, "The Edge Markets", label, aliases))
    all_news.extend(_fetch_rss_filtered(_STAR_BUSINESS_RSS, "The Star", label, aliases))
    all_news.extend(_fetch_rss_filtered(_MALAYSIAN_RESERVE_RSS, "The Malaysian Reserve", label, aliases))
    all_news.extend(_fetch_rss_filtered(_NST_BUSINESS_RSS, "New Straits Times", label, aliases))

    filtered = [
        n for n in all_news
        if _is_about_stock(n["title"], label, aliases, broker_aliases)
        and _is_recent(n["_dt"], max_age_days)
        and n.get("source", "").lower() not in _EXCLUDED_SOURCES
    ]
    filtered = _deduplicate(filtered)
    filtered.sort(key=lambda n: n["_dt"], reverse=True)

    analyst_sources = []
    for n in filtered:
        if _is_broker_report(n["title"]):
            item = dict(n)
            item.pop("_dt", None)
            analyst_sources.append(item)
        if len(analyst_sources) >= 5:
            break

    news = []
    for n in filtered[:max_news]:
        n.pop("_dt", None)
        news.append(n)

    return news, analyst_sources


def _fetch_klci_news(max_age_days: int = 7) -> list:
    queries = [
        "KLCI Bursa Malaysia index",
        '"Bursa Malaysia" market index',
        '"FTSE Bursa Malaysia KLCI"',
    ]
    seen, news = set(), []
    for query in queries:
        url = f"https://news.google.com/rss/search?q={quote(query)}&hl=en-MY&gl=MY&ceid=MY:en"
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                title = entry.get("title", "")
                key = " ".join(title.lower().split())
                if not title or key in seen:
                    continue
                dt = _parse_rss_datetime(entry)
                if not _is_recent(dt, max_age_days):
                    continue
                seen.add(key)
                news.append(_make_news_item(
                    title,
                    entry.get("link", "#"),
                    (entry.get("source") or {}).get("title", "Google News"),
                    dt,
                ))
        except Exception:
            continue

    news.sort(key=lambda n: n["_dt"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    result = []
    for n in news[:3]:
        n.pop("_dt", None)
        result.append(n)
    return result
