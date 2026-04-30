import feedparser
import yfinance as yf
from datetime import datetime
from email.utils import parsedate_to_datetime
from urllib.parse import quote
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

_analyzer = SentimentIntensityAnalyzer()


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


def _fetch_google_news(label: str, max_news: int) -> list:
    url = f"https://news.google.com/rss/search?q={quote(label + ' Bursa Malaysia')}&hl=en-MY&gl=MY&ceid=MY:en"
    try:
        feed = feedparser.parse(url)
        news = []
        for entry in feed.entries[:max_news]:
            title = entry.get("title", "")
            if not title:
                continue
            try:
                pub_date = parsedate_to_datetime(entry.get("published", "")).strftime("%-d %b %Y")
            except Exception:
                pub_date = "N/A"
            news.append({
                "title": title,
                "sentiment": score_sentiment(title),
                "link": entry.get("link", "#"),
                "source": (entry.get("source") or {}).get("title", "Unknown"),
                "date": pub_date,
            })
        return news
    except Exception:
        return []


def _price_context(tk, current_str: str, tz) -> str:
    if current_str == "N/A":
        return ""
    try:
        current = float(current_str)
        hist = tk.history(period="35d")
        if hist.empty:
            return ""
        hist.index = hist.index.tz_convert(tz)
        past = hist[hist.index.date < datetime.now(tz).date()]["Close"]
        if past.empty:
            return ""

        parts = []
        if len(past) >= 1:
            yest = past.iloc[-1]
            pct = ((current - yest) / yest) * 100
            parts.append(f"{'↑' if pct >= 0 else '↓'} {abs(pct):.1f}% vs yesterday (MYR {yest:.3f})")
        if len(past) >= 5:
            wk_avg = past.tail(5).mean()
            pct = ((current - wk_avg) / wk_avg) * 100
            parts.append(f"{'↑' if pct >= 0 else '↓'} {abs(pct):.1f}% vs last week avg (MYR {wk_avg:.3f})")
        if len(past) >= 20:
            mo_avg = past.tail(20).mean()
            pct = ((current - mo_avg) / mo_avg) * 100
            parts.append(f"{'↑' if pct >= 0 else '↓'} {abs(pct):.1f}% vs last month avg (MYR {mo_avg:.3f})")

        return f"At MYR {current_str}, the price is {' · '.join(parts)}." if parts else ""
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

        result["news"] = _fetch_google_news(label, max_news)

    except Exception as e:
        print(f"Warning: failed to fetch data for {ticker}: {e}")

    return result
