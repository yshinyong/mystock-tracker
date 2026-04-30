# MyStock Tracker

Sends a daily HTML email summarising Bursa Malaysia stock prices, 52-week ranges,
analyst target prices, and latest news with sentiment — automatically at 5pm MYT.

---

## What the email includes (per stock)

- Current price with comparison vs yesterday, last week avg, and last month avg
- Price vs 52-week high and low
- Analyst target prices (low / mean / high) — source: Yahoo Finance
- Up to 3 latest news headlines with sentiment (Positive / Neutral / Negative), source, and date

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

### 1. Create a virtual environment and install dependencies

```bash
cd ~/Downloads/mystock-tracker
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
source .venv/bin/activate   # if not already activated
python stock_summary.py
```

Check your inbox. If no email arrives, see Troubleshooting below.

---

## Scheduling (runs daily at 5pm MYT)

5pm MYT = 9am UTC. Add to crontab:

```bash
crontab -e
```

Paste this line (uses the venv Python):

```
0 9 * * * /path/to/mystock-tracker/.venv/bin/python /path/to/mystock-tracker/stock_summary.py >> /tmp/mystock.log 2>&1
```

Replace `/path/to/mystock-tracker` with the actual path on your machine.

Verify it was saved:

```bash
crontab -l
```

Logs go to `/tmp/mystock.log` — check there if something goes wrong.

---

## Adding more stocks

Edit `params.yaml` only — no code changes needed:

```yaml
stocks:
  - ticker: "5280.KL"
    label: "KIPREIT"
  - ticker: "1066.KL"
    label: "RHBBANK"
  - ticker: "1155.KL"    # add new stocks here
    label: "MAYBANK"
```

Use the Yahoo Finance ticker with `.KL` suffix for Bursa stocks.
Look up the correct ticker at [finance.yahoo.com](https://finance.yahoo.com) — search for the stock name and check the symbol shown (e.g. RHBBANK is `1066.KL`, not `RHBBANK.KL`).

---

## File structure

```
mystock-tracker/
├── params.yaml           # Stock list and email subject — edit to add stocks
├── .env                  # Your Gmail credentials — never commit this
├── .env.example          # Template for .env
├── .gitignore
├── stock_summary.py      # Entry point — config, orchestration, send email
├── fetcher.py            # Data fetching — yfinance, Google News, sentiment
├── email_renderer.py     # HTML email assembly
├── email_template.html   # Outer email layout (header, footer)
├── requirements.txt      # Python dependencies
└── README.md             # This file
```

---

## Data sources

| Data | Source |
|---|---|
| Stock price & 52-week range | Yahoo Finance (`yfinance`) — may be delayed 15–20 min |
| Price history (yesterday / week / month avg) | Yahoo Finance (`yfinance`) |
| Analyst target prices | Yahoo Finance analyst consensus |
| News | Google News RSS — free, no API key required |
| Sentiment analysis | VADER (rule-based, optimised for short headlines) |

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `Missing env variable` error | Check `.env` exists in the project folder and has no typos |
| `Gmail authentication failed` | Re-generate the App Password; make sure 2FA is still ON |
| All prices show `N/A` | Yahoo Finance may be rate-limiting; try again in a few minutes |
| No news shown | Google News found nothing for that stock name; try a broader label |
| Email not arriving | Check spam folder; also check `/tmp/mystock.log` for errors |
| Cron not firing | Run `crontab -l` to confirm the entry exists; check system clock |
| `ModuleNotFoundError` | Run `source .venv/bin/activate` then `pip install -r requirements.txt` |
