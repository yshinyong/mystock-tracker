import feedparser
import yfinance as yf
from datetime import datetime
from email.utils import parsedate_to_datetime
from urllib.parse import quote
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

_analyzer = SentimentIntensityAnalyzer()

_EDGE_MARKETS_RSS = "https://www.theedgemarkets.com/rss"
_STAR_BUSINESS_RSS = "https://www.thestar.com.my/rss/business/business-news"
_MALAYSIAN_RESERVE_RSS = "https://themalaysianreserve.com/feed/"
_NST_BUSINESS_RSS = "https://www.nst.com.my/business.rss"


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


def _make_news_item(title, link, source, date):
    return {
        "title": title,
        "sentiment": score_sentiment(title),
        "link": link,
        "source": source,
        "date": date,
    }


def _parse_rss_date(entry) -> str:
    for field in ("published", "updated"):
        raw = entry.get(field, "")
        if raw:
            try:
                return parsedate_to_datetime(raw).strftime("%-d %b %Y")
            except Exception:
                pass
    return "N/A"


def _fetch_google_news(label: str, ticker: str, max_news: int) -> list:
    code = ticker.split(".")[0]  # "5280" from "5280.KL"
    queries = [
        f"{label} Bursa Malaysia",
        f"{code} {label} KLSE",
    ]
    seen_titles = set()
    news = []
    for query in queries:
        url = f"https://news.google.com/rss/search?q={quote(query)}&hl=en-MY&gl=MY&ceid=MY:en"
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                title = entry.get("title", "")
                if not title or title in seen_titles:
                    continue
                seen_titles.add(title)
                news.append(_make_news_item(
                    title,
                    entry.get("link", "#"),
                    (entry.get("source") or {}).get("title", "Google News"),
                    _parse_rss_date(entry),
                ))
        except Exception:
            continue
    return news


def _fetch_yfinance_news(tk, max_news: int) -> list:
    try:
        raw = getattr(tk, "news", None) or []
        # yfinance >= 0.2.x may nest news under a key
        if isinstance(raw, dict):
            raw = list(raw.values())[0] if raw else []
        news = []
        for item in raw[:max_news * 3]:
            if not isinstance(item, dict):
                continue
            title = item.get("title", "")
            if not title:
                continue
            pub_ts = item.get("providerPublishTime")
            try:
                pub_date = datetime.fromtimestamp(pub_ts).strftime("%-d %b %Y") if pub_ts else "N/A"
            except Exception:
                pub_date = "N/A"
            news.append(_make_news_item(
                title,
                item.get("link", "#"),
                item.get("publisher", "Yahoo Finance"),
                pub_date,
            ))
        return news
    except Exception:
        return []


def _fetch_rss_filtered(url: str, source_name: str, label: str, max_news: int) -> list:
    """Fetch a generic RSS feed and return entries mentioning the stock label."""
    try:
        feed = feedparser.parse(url)
        label_lower = label.lower()
        news = []
        for entry in feed.entries:
            title = entry.get("title", "")
            summary = entry.get("summary", "")
            if not title:
                continue
            if label_lower not in title.lower() and label_lower not in summary.lower():
                continue
            src = (entry.get("source") or {}).get("title", source_name)
            news.append(_make_news_item(title, entry.get("link", "#"), src, _parse_rss_date(entry)))
            if len(news) >= max_news:
                break
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


def _fetch_all_news(tk, label: str, ticker: str, max_news: int) -> list:
    all_news = []
    all_news.extend(_fetch_yfinance_news(tk, max_news))
    all_news.extend(_fetch_google_news(label, ticker, max_news))
    all_news.extend(_fetch_rss_filtered(_EDGE_MARKETS_RSS, "The Edge Markets", label, max_news))
    all_news.extend(_fetch_rss_filtered(_STAR_BUSINESS_RSS, "The Star", label, max_news))
    all_news.extend(_fetch_rss_filtered(_MALAYSIAN_RESERVE_RSS, "The Malaysian Reserve", label, max_news))
    all_news.extend(_fetch_rss_filtered(_NST_BUSINESS_RSS, "New Straits Times", label, max_news))
    return _deduplicate(all_news)[:max_news]


def _price_context(tk, current_str: str, tz) -> str:
    if current_str == "N/A":
        return ""
    try:
        current = float(current_str)
        hist = tk.history(period="70d")
        if hist.empty:
            return ""
        hist.index = hist.index.tz_convert(tz)
        past = hist[hist.index.date < datetime.now(tz).date()]["Close"]
        if past.empty:
            return ""

        def _fmt_line(pct, ref_price, label):
            up = pct >= 0
            arrow = "↑" if up else "↓"
            color = "#2e7d32" if up else "#c62828"
            return f'<span style="color:{color}">{arrow} {abs(pct):.1f}% vs {label} (MYR {ref_price:.3f})</span>'

        parts = []
        if len(past) >= 1:
            yest = past.iloc[-1]
            parts.append(_fmt_line((current - yest) / yest * 100, yest, "yesterday"))
        if len(past) >= 5:
            wk_avg = past.tail(5).mean()
            parts.append(_fmt_line((current - wk_avg) / wk_avg * 100, wk_avg, "last week avg"))
        if len(past) >= 20:
            mo_avg = past.tail(20).mean()
            parts.append(_fmt_line((current - mo_avg) / mo_avg * 100, mo_avg, "last month avg"))
        if len(past) >= 60:
            mo3_avg = past.tail(60).mean()
            parts.append(_fmt_line((current - mo3_avg) / mo3_avg * 100, mo3_avg, "last 3 months avg"))

        return f"At MYR {current_str}:<br>" + "<br>".join(parts) if parts else ""
    except Exception:
        return ""


def fetch_stock_data(ticker: str, label: str, max_news: int, tz) -> dict:
    result = {
        "label": label, "ticker": ticker,
        "current_price": "N/A", "price_context": "",
        "week52_high": "N/A", "week52_low": "N/A",
        "price_vs_high": "N/A", "price_vs_low": "N/A",
        "analyst_low": "N/A", "analyst_mean": "N/A", "analyst_high": "N/A",
        "news": [],
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
            result["price_context"] = _price_context(tk, result["current_price"], tz)
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

        result["news"] = _fetch_all_news(tk, label, ticker, max_news)

    except Exception as e:
        print(f"Warning: failed to fetch data for {ticker}: {e}")

    return result
