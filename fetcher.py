import feedparser
import requests
import yfinance as yf
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

_analyzer = SentimentIntensityAnalyzer()

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


def score_sentiment(text: str) -> str:
    compound = _analyzer.polarity_scores(text)["compound"]
    if compound >= 0.05:
        return "Positive"
    if compound <= -0.05:
        return "Negative"
    return "Neutral"


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


_BROKER_REPORT_KEYWORDS = (
    "target price", "price target", " tp ", "tp:", "tp of", "tp to",
    "buy", "sell", "hold", "overweight", "underweight", "outperform",
    "underperform", "neutral", "upgrade", "downgrade", "initiate",
    "reiterate", "maintain",
)

_EXCLUDED_SOURCES = {"ad hoc news"}


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


def _compute_price_comparisons(tk, current_str: str, tz) -> list:
    """Return list of {label, pct, ref_price} for each available time window."""
    if current_str == "N/A":
        return []
    try:
        current = float(current_str)
        hist = tk.history(period="70d")
        if hist.empty:
            return []
        hist.index = hist.index.tz_convert(tz)
        past = hist[hist.index.date < datetime.now(tz).date()]["Close"]
        if past.empty:
            return []

        comparisons = []
        if len(past) >= 1:
            ref = past.iloc[-1]
            comparisons.append({"label": "yesterday", "pct": (current - ref) / ref * 100, "ref_price": ref})
        if len(past) >= 5:
            ref = past.tail(5).mean()
            comparisons.append({"label": "last week avg", "pct": (current - ref) / ref * 100, "ref_price": ref})
        if len(past) >= 20:
            ref = past.tail(20).mean()
            comparisons.append({"label": "last month avg", "pct": (current - ref) / ref * 100, "ref_price": ref})
        if len(past) >= 60:
            ref = past.tail(60).mean()
            comparisons.append({"label": "last 3 months avg", "pct": (current - ref) / ref * 100, "ref_price": ref})
        return comparisons
    except Exception:
        return []


def _price_context_html(current_str: str, comparisons: list) -> str:
    if not comparisons:
        return ""

    def _fmt_line(pct, ref_price, label):
        up = pct >= 0
        arrow = "↑" if up else "↓"
        color = "#2e7d32" if up else "#c62828"
        return f'<span style="color:{color}">{arrow} {abs(pct):.1f}% vs {label} (MYR {ref_price:.3f})</span>'

    parts = [_fmt_line(c["pct"], c["ref_price"], c["label"]) for c in comparisons]
    return f"At MYR {current_str}:<br>" + "<br>".join(parts)


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


def fetch_stock_data(ticker: str, label: str, aliases: list, broker_aliases: list,
                     max_news: int, max_age_days: int, tz) -> dict:
    result = {
        "label": label, "ticker": ticker,
        "current_price": "N/A", "price_context": "",
        "price_comparisons": [],
        "week52_high": "N/A", "week52_low": "N/A",
        "price_vs_high": "N/A", "price_vs_low": "N/A",
        "analyst_low": "N/A", "analyst_mean": "N/A", "analyst_high": "N/A",
        "analyst_sources": [],
        "news": [],
        "klse_comments": [],
    }
    try:
        tk = yf.Ticker(ticker)

        try:
            info = tk.info
            current = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")
            high52, low52 = info.get("fiftyTwoWeekHigh"), info.get("fiftyTwoWeekLow")
            result["current_price"] = _fmt_price(current)
            result["week52_high"] = _fmt_price(high52)
            result["week52_low"] = _fmt_price(low52)
            if current is not None:
                result["price_vs_high"] = _pct_diff(current, high52, "52W High")
                result["price_vs_low"] = _pct_diff(current, low52, "52W Low")
        except Exception:
            pass

        try:
            comparisons = _compute_price_comparisons(tk, result["current_price"], tz)
            result["price_comparisons"] = comparisons
            result["price_context"] = _price_context_html(result["current_price"], comparisons)
        except Exception:
            pass

        try:
            apt = tk.analyst_price_targets
            if apt is not None:
                result["analyst_low"] = _fmt_price(apt.get("low"))
                result["analyst_mean"] = _fmt_price(apt.get("mean"))
                result["analyst_high"] = _fmt_price(apt.get("high"))
        except Exception:
            pass

        result["news"], result["analyst_sources"] = _fetch_all_news(
            tk, label, ticker, aliases, broker_aliases, max_news, max_age_days,
        )

        klse_code = ticker.split(".")[0]
        result["klse_comments"] = _fetch_klse_comments(klse_code, days=7)

    except Exception as e:
        print(f"Warning: failed to fetch data for {ticker}: {e}")

    return result


def fetch_klci_data(tz) -> dict:
    result = {"current": "N/A", "date": "N/A", "comparisons": [], "ytd_history": []}
    try:
        tk = yf.Ticker("^KLSE")
        now = datetime.now(tz)

        hist = tk.history(period="1y")
        if hist.empty:
            return result
        hist.index = hist.index.tz_convert(tz)

        all_close = hist["Close"]
        today_date = now.date()

        today_bars = all_close[all_close.index.date == today_date]
        past = all_close[all_close.index.date < today_date]

        if not today_bars.empty:
            current = float(today_bars.iloc[-1])
            current_date = today_date
        elif not past.empty:
            current = float(past.iloc[-1])
            current_date = past.index[-1].date()
        else:
            return result

        result["current"] = f"{current:.2f}"
        result["date"] = current_date.strftime("%-d %b %Y")

        ytd_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        ytd = all_close[all_close.index >= ytd_start]
        result["ytd_history"] = [
            (d.strftime("%Y-%m-%d"), float(v))
            for d, v in ytd.items()
        ]

        comparisons = []
        if len(past) >= 1:
            ref = float(past.iloc[-1])
            comparisons.append({"label": "yesterday", "pct": (current - ref) / ref * 100, "ref": ref})
        if len(past) >= 5:
            ref = float(past.tail(5).mean())
            comparisons.append({"label": "last week avg", "pct": (current - ref) / ref * 100, "ref": ref})
        if len(past) >= 20:
            ref = float(past.tail(20).mean())
            comparisons.append({"label": "last month avg", "pct": (current - ref) / ref * 100, "ref": ref})
        if len(past) >= 60:
            ref = float(past.tail(60).mean())
            comparisons.append({"label": "last 3 months avg", "pct": (current - ref) / ref * 100, "ref": ref})

        result["comparisons"] = comparisons
    except Exception as e:
        print(f"Warning: failed to fetch KLCI data: {e}")
    return result
