# MyStock Tracker

Sends a daily HTML email summarising Bursa Malaysia stock prices, analyst targets,
latest news, community comments, and a KLCI market overview — automatically at 7pm MYT via launchd.

---

## What the email includes

### Executive Summary (top of email)
- Flags any stock where **all** price comparisons (yesterday, last week avg, last month avg, last 3 months avg) are uniformly positive or uniformly negative

### Per stock
- Current price with % change vs yesterday, last week avg, last month avg, and last 3 months avg
- Price vs 52-week high and low
- Analyst target prices (low / mean / high) from Yahoo Finance, with links to related analyst reports
- Up to 6 recent news headlines with sentiment (Positive / Neutral / Negative), source, and date
- Community comments from KLSE Screener for the past 7 days

### FTSE Bursa Malaysia KLCI (bottom of email)
- Current index value with % change vs yesterday, last week avg, last month avg, and last 3 months avg
- 3 key recent news headlines driving the market move, with sentiment
- YTD line chart (embedded inline — no external image load required)

---

## Tracked stocks

| Ticker | Label |
|---|---|
| 5280.KL | KIPREIT |
| 1066.KL | RHBBANK |
| 1295.KL | PBBANK |
| 1155.KL | MAYBANK |
| 5099.KL | CAPITALA |
| 6033.KL | PETGAS |

---

## Prerequisites

- Python 3.9 or newer
- A Gmail account with **2-Factor Authentication enabled**
- A **Gmail App Password** (16-character code, not your normal password)

### How to get a Gmail App Password

1. Go to [myaccount.google.com](https://myaccount.google.com)
2. Security → 2-Step Verification (must be ON)
3. Security → App Passwords
4. Select "Mail" + "Mac" → Generate
5. Copy the 16-character code shown

---

## Setup

### 1. Clone and install dependencies

```bash
cd ~/mystock-tracker
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Create your `.env` file

```bash
cp .env.example .env
```

Open `.env` and fill in your details:

```
GMAIL_SENDER=your_gmail@gmail.com
GMAIL_RECIPIENT=your_gmail@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
```

`GMAIL_SENDER` and `GMAIL_RECIPIENT` can be the same address.

> **Never commit `.env` to git.** It is already in `.gitignore`.

### 3. Test manually

```bash
source .venv/bin/activate
python stock_summary.py
```

Check your inbox. If no email arrives, see Troubleshooting below.

---

## Scheduling (runs daily at 7pm MYT via launchd)

A launchd plist is used instead of cron so the job runs even if the Mac was asleep at the scheduled time.

The plist is at `~/Library/LaunchAgents/com.shin.mystock-tracker.plist`. To load or reload it:

```bash
launchctl unload ~/Library/LaunchAgents/com.shin.mystock-tracker.plist
launchctl load ~/Library/LaunchAgents/com.shin.mystock-tracker.plist
```

To verify it is loaded:

```bash
launchctl list | grep mystock-tracker
```

Logs go to `/tmp/mystock.log` — check there if something goes wrong.

---

## Adding or removing stocks

Edit `params.yaml` only — no code changes needed:

```yaml
stocks:
  - ticker: "5280.KL"
    label: "KIPREIT"
    aliases: ["KIP REIT", "KIP-REIT"]       # optional: extra names for news matching
  - ticker: "1066.KL"
    label: "RHBBANK"
    aliases: ["RHB Bank", "RHB"]
    broker_aliases: ["RHB Research", "RHB Investment Bank"]  # optional: filter out own-broker headlines
```

Use the Yahoo Finance ticker with `.KL` suffix for Bursa stocks.
Look up the correct ticker at [finance.yahoo.com](https://finance.yahoo.com).

---

## File structure

```
mystock-tracker/
├── params.yaml           # Stock list and settings — edit to add/remove stocks
├── .env                  # Gmail credentials — never commit this
├── .env.example          # Template for .env
├── .gitignore
├── stock_summary.py      # Entry point — orchestration and email sending
├── fetcher.py            # Data fetching — yfinance, Google News, KLSE Screener, KLCI
├── email_renderer.py     # HTML email and chart assembly
├── email_template.html   # Outer email layout (header, footer)
├── requirements.txt      # Python dependencies
└── README.md             # This file
```

---

## Data sources

| Data | Source |
|---|---|
| Stock price & 52-week range | Yahoo Finance (`yfinance`) — may be delayed 15–20 min |
| Price history (yesterday / week / month / 3-month avg) | Yahoo Finance (`yfinance`) |
| Analyst target prices | Yahoo Finance analyst consensus |
| Analyst report links | Google News RSS |
| News & sentiment | Google News RSS + The Edge Markets, The Star, Malaysian Reserve, NST RSS feeds |
| Sentiment scoring | VADER (rule-based, optimised for short headlines) |
| Community comments | KLSE Screener (past 7 days) |
| KLCI index data & chart | Yahoo Finance (`^KLSE`) |
| KLCI news | Google News RSS |

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `Missing env variable` error | Check `.env` exists in the project folder and has no typos |
| `Gmail authentication failed` | Re-generate the App Password; make sure 2FA is still ON |
| All prices show `N/A` | Yahoo Finance may be rate-limiting; try again in a few minutes |
| No news shown | Google News found nothing for that stock name; try a broader alias in `params.yaml` |
| No KLSE Screener comments | The stock may have no comments in the past 7 days — this is normal |
| KLCI chart missing | Ensure `matplotlib` is installed: `pip install -r requirements.txt` |
| Email not arriving | Check spam folder; also check `/tmp/mystock.log` for errors |
| launchd job not firing | Run `launchctl list \| grep mystock-tracker` to confirm it is loaded |
| `ModuleNotFoundError` | Run `source .venv/bin/activate` then `pip install -r requirements.txt` |
