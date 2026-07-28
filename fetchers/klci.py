from datetime import datetime

import yfinance as yf

from .news import _fetch_klci_news


def fetch_klci_data(tz) -> dict:
    result = {"current": "N/A", "date": "N/A", "comparisons": [], "ytd_history": [], "news": []}
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
        result["news"] = _fetch_klci_news()
    except Exception as e:
        print(f"Warning: failed to fetch KLCI data: {e}")
    return result
