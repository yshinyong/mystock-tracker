from datetime import datetime


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
