# TicketPulse 🎯

> **Headless browser pipeline that unlocks Freshdesk ticket activity data — restricted from the API — and transforms it into structured, analysis-ready reports for tracking employee performance, team workload, and response timelines.**

---

## Why This Exists

Freshdesk exposes most ticket data through its REST API — but **ticket activity logs are not**. The full timeline of who did what and when (agent assignments, status changes, replies, notes, automations) is only rendered in the browser UI.

This project solves that by **automating a real browser session** using Playwright to navigate to each ticket, expand the activity panel, scroll through all entries, and capture the raw text — exactly as a human agent would see it.

---

## What It Does

```
Ticket IDs (Excel)
       │
       ▼
┌─────────────────────────────┐
│   scrape_fd_activities.py   │  ← Headless Chromium via Playwright
│                             │    Injects auth cookies, opens each
│   Browser → Ticket Page     │    ticket, clicks Activities panel,
│   → Expand All → Capture   │    loads all entries, captures text
└────────────┬────────────────┘
             │  ticket_activities_scraped1.xlsx
             ▼
┌──────────────────────────────────┐
│  final_parse_fd_activities.py    │  ← Regex + rule-based NLP parser
│                                  │    Extracts: actor, action tag,
│  Raw text → Structured rows      │    action text, date, time (IST)
└────────────┬─────────────────────┘
             │  ticket_activities_structured1.xlsx
             ▼
     📊 Excel Report on Desktop
```

---

## Output Columns

| Column | Description |
|---|---|
| `Ticket` | Freshdesk ticket ID |
| `Actioned By` | Agent name or `System` / `Customer Support` |
| `Action Tag` | Classified action type (e.g. `status updated`, `replied`) |
| `Action Text` | Full description of what was done |
| `Date` | Date of the activity (`Mon, 01 Jan 2026`) |
| `Time (IST)` | Time of activity in IST (`09:30 AM`) |

---

## Analysis Use Cases

Once structured, the data enables:

- **Agent productivity tracking** — how many actions each agent performed per day/week
- **Response time analysis** — time between ticket creation and first reply
- **Status flow mapping** — how tickets move through Open → Pending → Resolved
- **After-hours activity detection** — identify work done outside business hours
- **Automation audit** — track how often automations fire vs manual actions
- **Team workload distribution** — compare activity volume across agents and groups

---

## Why Not Use the Freshdesk API?

The Freshdesk REST API provides ticket metadata (subject, status, assignee) but **does not expose the activity/audit log** through any endpoint. The timeline of events — who replied, when a status changed, which agent was assigned at what time — is exclusively available in the **browser UI** under the Activities panel.

This pipeline replicates that browser interaction programmatically:

```
API ✗  →  activity log is browser-only
Browser ✔ →  Playwright automates the session headlessly
```

---

## Tech Stack

| Tool | Purpose |
|---|---|
| [Playwright](https://playwright.dev/python/) | Headless Chromium browser automation |
| [pandas](https://pandas.pydata.org/) | Data processing and Excel I/O |
| [openpyxl](https://openpyxl.readthedocs.io/) | Excel file writing |
| Python `re` / `datetime` | Activity text parsing and time extraction |

---

## Project Structure

```
TicketPulse/
├── Scripts/
│   ├── scrape_fd_activities.py       # Stage 1: Browser scraper
│   ├── final_parse_fd_activities.py  # Stage 2: Text parser
│   └── Ticket_sheet2.xlsx            # Input: list of ticket IDs
├── requirements-to-run/
│   └── req                           # Run instructions & config notes
└── README.md
```

---

## Setup

```bash
# 1. Clone and enter the project
git clone https://github.com/your-username/ticketpulse.git
cd ticketpulse

# 2. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install pandas openpyxl playwright
playwright install chromium
```

---

## Running

**Step 1 — Add your ticket IDs**

Populate `Scripts/Ticket_sheet2.xlsx` with a `ticket_id` column containing the tickets you want to analyze.

**Step 2 — Set your auth cookies**

Open any Freshdesk ticket in Chrome → DevTools → Network tab → any request → Cookies.
Copy the 6 essential cookies and paste them into `COOKIE_STRING` at the top of `scrape_fd_activities.py`:

```python
COOKIE_STRING = (
    "__cf_bm=...; "
    "fd=...; "
    "helpdesk_url=...; "
    "helpdesk_node_session=...; "
    "user_credentials=...; "
    "session_token=..."
)
```

**Step 3 — Run the pipeline**

```bash
cd Scripts

# Scrape activity text from Freshdesk (headless)
python3 scrape_fd_activities.py

# Parse raw text into structured Excel report
python3 final_parse_fd_activities.py
```

Output saved to `~/Desktop/ticket_activities_structured1.xlsx`.

---

## How Auth Works

Instead of storing a login session file (which breaks across machines), this project injects **6 browser cookies** directly into the Playwright context:

| Cookie | Role |
|---|---|
| `__cf_bm` | Cloudflare bot protection bypass |
| `fd` | Freshdesk session identifier |
| `helpdesk_url` | Domain routing |
| `helpdesk_node_session` | Server-side session |
| `user_credentials` | Auth token |
| `session_token` | Session authentication |

Cookies expire periodically — refresh them from DevTools when needed.

---

## Limitations

- Cookies must be manually refreshed when they expire (typically every few days)
- Scraping speed is intentionally throttled (1–10s random delay) to avoid rate limiting
- Works only for accounts with browser access to the ticket activity panel

---

*Built to extract insights from support operations data that the official API doesn't expose.*
