import os
import smtplib
import yaml
import pytz
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv

from fetcher import fetch_stock_data, fetch_klci_data
from email_renderer import build_html_email


def load_config() -> dict:
    with open("params.yaml", "r") as f:
        config = yaml.safe_load(f)

    load_dotenv()
    sender = os.environ.get("GMAIL_SENDER")
    recipient = os.environ.get("GMAIL_RECIPIENT")
    password = os.environ.get("GMAIL_APP_PASSWORD")

    if not sender:
        raise RuntimeError("Missing env variable: GMAIL_SENDER")
    if not recipient:
        raise RuntimeError("Missing env variable: GMAIL_RECIPIENT")
    if not password:
        raise RuntimeError("Missing env variable: GMAIL_APP_PASSWORD")

    config["sender"] = sender
    config["recipient"] = recipient
    config["password"] = password
    return config


def send_email(html_body: str, config: dict, date_str: str):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = config["email"]["subject"].format(date=date_str)
    msg["From"] = config["sender"]
    msg["To"] = config["recipient"]
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(config["sender"], config["password"])
            server.sendmail(config["sender"], config["recipient"], msg.as_string())
    except smtplib.SMTPAuthenticationError:
        raise RuntimeError("Gmail authentication failed. Check GMAIL_APP_PASSWORD in your .env file.")
    except Exception as e:
        raise RuntimeError(f"Failed to send email: {e}")


def main():
    config = load_config()
    tz = pytz.timezone(config["settings"]["timezone"])
    now = datetime.now(tz)
    date_str = now.strftime("%d %b %Y")
    timestamp_str = now.strftime("%H:%M")
    max_news = config["settings"]["max_news_per_stock"]
    max_age_days = config["settings"].get("max_news_age_days", 60)

    print(f"Fetching data for {len(config['stocks'])} stock(s)...")
    stock_data_list = []
    for stock in config["stocks"]:
        print(f"  → {stock['label']} ({stock['ticker']})")
        stock_data_list.append(fetch_stock_data(
            ticker=stock["ticker"],
            label=stock["label"],
            aliases=stock.get("aliases", []),
            broker_aliases=stock.get("broker_aliases", []),
            max_news=max_news,
            max_age_days=max_age_days,
            tz=tz,
        ))

    print("Fetching KLCI data...")
    klci = fetch_klci_data(tz)

    print("Building email...")
    html = build_html_email(stock_data_list, date_str, timestamp_str, klci_data=klci)

    print("Sending email...")
    send_email(html, config, date_str)
    print(f"Done. Email sent to {config['recipient']} at {timestamp_str} MYT.")


if __name__ == "__main__":
    main()
