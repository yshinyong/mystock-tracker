from pathlib import Path

_SENTIMENT_COLOR = {
    "Positive": "#2e7d32",
    "Negative": "#c62828",
    "Neutral":  "#757575",
}

_TEMPLATE = Path(__file__).with_name("email_template.html").read_text()


def _news_item(n: dict) -> str:
    color = _SENTIMENT_COLOR.get(n["sentiment"], "#757575")
    return f"""
    <li style="margin-bottom:12px;">
      <span style="display:inline-block;padding:2px 7px;border-radius:4px;
                   background:{color};color:#fff;font-size:11px;font-weight:600;
                   margin-right:8px;">{n["sentiment"]}</span>
      <a href="{n["link"]}" style="color:#1565c0;text-decoration:none;">{n["title"]}</a>
      <div style="margin-top:3px;font-size:11px;color:#9e9e9e;">
        {n["source"]} &nbsp;·&nbsp; {n["date"]}
      </div>
    </li>"""


def _comment_item(c: dict) -> str:
    likes_html = (
        f'<span style="margin-left:8px;font-size:11px;color:#757575;">👍 {c["likes"]}</span>'
        if c["likes"] > 0 else ""
    )
    return f"""
    <li style="margin-bottom:14px;padding:10px 12px;background:#f9f9f9;border-left:3px solid #c5cae9;border-radius:4px;">
      <div style="font-size:12px;font-weight:600;color:#1a237e;margin-bottom:4px;">
        {c["username"]}{likes_html}
      </div>
      <div style="font-size:13px;color:#212121;line-height:1.5;">{c["message"]}</div>
      <div style="margin-top:4px;font-size:11px;color:#9e9e9e;">{c["date"]}</div>
    </li>"""


def _analyst_source_item(n: dict) -> str:
    return (
        f'<li style="margin-bottom:5px;font-size:11px;">'
        f'<a href="{n["link"]}" style="color:#1565c0;text-decoration:none;">{n["title"]}</a>'
        f' <span style="color:#9e9e9e;">— {n["source"]} · {n["date"]}</span>'
        f'</li>'
    )


def _stock_card(s: dict) -> str:
    news_html = "".join(_news_item(n) for n in s["news"]) if s["news"] \
        else "<li style='color:#757575;'>No news available.</li>"
    price_context_html = f'<p style="margin:0 0 10px;font-size:13px;color:#424242;">{s["price_context"]}</p>' \
        if s["price_context"] else ""

    analyst_sources = s.get("analyst_sources", [])
    if analyst_sources:
        items = "".join(_analyst_source_item(n) for n in analyst_sources)
        analyst_sources_html = (
            f'<p style="margin:4px 0 4px;font-size:11px;color:#9e9e9e;">Related analyst reports:</p>'
            f'<ul style="margin:0 0 16px;padding-left:0;list-style:none;">{items}</ul>'
        )
    else:
        analyst_sources_html = '<p style="margin:4px 0 16px;font-size:11px;color:#9e9e9e;">No recent analyst reports found.</p>'

    comments = s.get("klse_comments", [])
    comments_html = "".join(_comment_item(c) for c in comments) if comments \
        else "<li style='color:#757575;'>No community comments in the past 7 days.</li>"
    klse_code = s["ticker"].split(".")[0]
    klse_url = f"https://www.klsescreener.com/v2/comments/all/stock/{klse_code}"

    return f"""
    <div style="background:#fff;border:1px solid #e0e0e0;border-radius:8px;padding:20px 24px;margin-bottom:24px;">
      <h2 style="margin:0 0 16px;font-size:18px;color:#1a237e;">
        {s["label"]} <span style="font-size:13px;color:#757575;font-weight:normal;">({s["ticker"]})</span>
      </h2>

      <h3 style="margin:0 0 8px;font-size:13px;color:#424242;text-transform:uppercase;letter-spacing:.5px;">Price</h3>
      {price_context_html}
      <table style="border-collapse:collapse;margin-bottom:16px;width:100%;max-width:420px;">
        <tr style="background:#f5f5f5;">
          <td style="padding:7px 14px;font-size:13px;color:#616161;">Current Price</td>
          <td style="padding:7px 14px;font-size:13px;font-weight:600;color:#212121;">MYR {s["current_price"]}</td>
        </tr>
        <tr>
          <td style="padding:7px 14px;font-size:13px;color:#616161;">52-Week High</td>
          <td style="padding:7px 14px;font-size:13px;color:#212121;">
            MYR {s["week52_high"]} <span style="font-size:12px;color:#757575;">({s["price_vs_high"]})</span>
          </td>
        </tr>
        <tr style="background:#f5f5f5;">
          <td style="padding:7px 14px;font-size:13px;color:#616161;">52-Week Low</td>
          <td style="padding:7px 14px;font-size:13px;color:#212121;">
            MYR {s["week52_low"]} <span style="font-size:12px;color:#757575;">({s["price_vs_low"]})</span>
          </td>
        </tr>
      </table>

      <h3 style="margin:0 0 8px;font-size:13px;color:#424242;text-transform:uppercase;letter-spacing:.5px;">Analyst Target Prices</h3>
      <table style="border-collapse:collapse;width:100%;max-width:420px;">
        <tr style="background:#f5f5f5;">
          <td style="padding:7px 14px;font-size:13px;color:#616161;">Low</td>
          <td style="padding:7px 14px;font-size:13px;color:#212121;">MYR {s["analyst_low"]}</td>
        </tr>
        <tr>
          <td style="padding:7px 14px;font-size:13px;color:#616161;">Mean</td>
          <td style="padding:7px 14px;font-size:13px;color:#212121;">MYR {s["analyst_mean"]}</td>
        </tr>
        <tr style="background:#f5f5f5;">
          <td style="padding:7px 14px;font-size:13px;color:#616161;">High</td>
          <td style="padding:7px 14px;font-size:13px;color:#212121;">MYR {s["analyst_high"]}</td>
        </tr>
      </table>
      <p style="margin:4px 0 8px;font-size:11px;color:#9e9e9e;">Consensus via Yahoo Finance</p>
      {analyst_sources_html}

      <h3 style="margin:0 0 8px;font-size:13px;color:#424242;text-transform:uppercase;letter-spacing:.5px;">News</h3>
      <ul style="margin:0;padding-left:0;list-style:none;">{news_html}</ul>

      <h3 style="margin:16px 0 8px;font-size:13px;color:#424242;text-transform:uppercase;letter-spacing:.5px;">Community Comments (Past 7 Days)</h3>
      <ul style="margin:0;padding-left:0;list-style:none;">{comments_html}</ul>
      <p style="margin:4px 0 0;font-size:11px;color:#9e9e9e;">
        Source: <a href="{klse_url}" style="color:#9e9e9e;">KLSE Screener</a>
      </p>
    </div>"""


def _executive_summary(stock_data_list: list) -> str:
    all_green = []
    all_red = []
    for s in stock_data_list:
        comps = s.get("price_comparisons", [])
        if not comps:
            continue
        pcts = [c["pct"] for c in comps]
        if all(p > 0 for p in pcts):
            all_green.append(s)
        elif all(p < 0 for p in pcts):
            all_red.append(s)

    if not all_green and not all_red:
        return ""

    def _comp_line(s):
        parts = [
            f'{c["label"]}: {"+" if c["pct"] >= 0 else ""}{c["pct"]:.1f}%'
            for c in s["price_comparisons"]
        ]
        return f'<strong>{s["label"]}</strong> &mdash; ' + ", ".join(parts)

    sections = []
    if all_green:
        rows = "".join(
            f'<li style="margin-bottom:6px;font-size:13px;color:#212121;">{_comp_line(s)}</li>'
            for s in all_green
        )
        sections.append(f"""
        <div style="margin-bottom:12px;">
          <div style="font-weight:700;font-size:13px;color:#2e7d32;margin-bottom:6px;
                      text-transform:uppercase;letter-spacing:.5px;">All Positive</div>
          <ul style="margin:0;padding-left:0;list-style:none;">{rows}</ul>
        </div>""")

    if all_red:
        rows = "".join(
            f'<li style="margin-bottom:6px;font-size:13px;color:#212121;">{_comp_line(s)}</li>'
            for s in all_red
        )
        sections.append(f"""
        <div style="margin-bottom:0;">
          <div style="font-weight:700;font-size:13px;color:#c62828;margin-bottom:6px;
                      text-transform:uppercase;letter-spacing:.5px;">All Negative</div>
          <ul style="margin:0;padding-left:0;list-style:none;">{rows}</ul>
        </div>""")

    body = "".join(sections)
    return f"""
    <div style="background:#fff;border:1px solid #e0e0e0;border-radius:8px;
                padding:20px 24px;margin-top:16px;margin-bottom:8px;">
      <h2 style="margin:0 0 14px;font-size:15px;color:#1a237e;text-transform:uppercase;
                 letter-spacing:.5px;">Executive Summary</h2>
      {body}
    </div>"""


def build_html_email(stock_data_list: list, date_str: str, timestamp_str: str) -> str:
    cards = "".join(_stock_card(s) for s in stock_data_list)
    summary = _executive_summary(stock_data_list)
    return (
        _TEMPLATE
        .replace("{date_str}", date_str)
        .replace("{executive_summary}", summary)
        .replace("{cards}", cards)
        .replace("{timestamp_str}", timestamp_str)
    )
