import yfinance as yf

from .formatting import _fmt_price, _pct_diff
from .i3investor import _fetch_i3investor_announcements, _fetch_i3investor_targets
from .klse_screener import _fetch_klse_comments
from .news import _fetch_all_news
from .price import _compute_price_comparisons, _price_context_html


def fetch_stock_data(ticker: str, label: str, aliases: list, broker_aliases: list,
                     max_news: int, max_age_days: int, tz) -> dict:
    result = {
        "label": label, "ticker": ticker,
        "current_price": "N/A", "price_context": "",
        "price_comparisons": [],
        "week52_high": "N/A", "week52_low": "N/A",
        "price_vs_high": "N/A", "price_vs_low": "N/A",
        "analyst_targets": [],
        "analyst_sources": [],
        "news": [],
        "klse_comments": [],
        "announcements": [],
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

        result["news"], result["analyst_sources"] = _fetch_all_news(
            tk, label, ticker, aliases, broker_aliases, max_news, max_age_days,
        )

        klse_code = ticker.split(".")[0]
        result["analyst_targets"] = _fetch_i3investor_targets(klse_code)
        result["klse_comments"] = _fetch_klse_comments(klse_code, days=7)
        result["announcements"] = _fetch_i3investor_announcements(klse_code, days=7)

    except Exception as e:
        print(f"Warning: failed to fetch data for {ticker}: {e}")

    return result
