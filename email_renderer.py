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


def _stock_card(s: dict) -> str:
    news_html = "".join(_news_item(n) for n in s["news"]) if s["news"] \
        else "<li style='color:#757575;'>No news available.</li>"
    price_context_html = f'<p style="margin:0 0 10px;font-size:13px;color:#424242;">{s["price_context"]}</p>' \
        if s["price_context"] else ""
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
      <p style="margin:4px 0 16px;font-size:11px;color:#9e9e9e;">Source: Yahoo Finance (Analyst Consensus)</p>

      <h3 style="margin:0 0 8px;font-size:13px;color:#424242;text-transform:uppercase;letter-spacing:.5px;">News</h3>
      <ul style="margin:0;padding-left:0;list-style:none;">{news_html}</ul>
    </div>"""


def build_html_email(stock_data_list: list, date_str: str, timestamp_str: str) -> str:
    cards = "".join(_stock_card(s) for s in stock_data_list)
    return (
        _TEMPLATE
        .replace("{date_str}", date_str)
        .replace("{cards}", cards)
        .replace("{timestamp_str}", timestamp_str)
    )
