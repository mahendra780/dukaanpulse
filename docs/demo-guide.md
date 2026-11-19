# Isolated demo guide

Use this guide only for an isolated demonstration environment. The demo
generator is deliberately designed to refuse a production-like target, but
that safeguard is not a replacement for careful environment selection.

Do not commit a demo database URL, a JWT signing key, a password, a token, or
screenshots containing real data. The seeded names and values are synthetic.

## 1. Prepare an isolated database

1. Create a separate local PostgreSQL database or separate Neon branch/project
   for this demo. Do not point it at the live database.
2. Provision the schema through the repository's approved manual SQL process.
   The baseline file, backend/sql/000_baseline_schema.sql, is a reference dump,
   not an additive migration to rerun against a database that already has the
   baseline. Apply missing additive files 001, 002, and 003 in numeric order.
   See docs/deployment-checklist.md for the migration safeguards.
3. From backend, create a local environment file that Git ignores:

        Copy-Item .env.example .env.demo

4. Edit backend/.env.demo locally. Give DATABASE_URL the isolated database URL,
   give JWT_SECRET_KEY a newly generated value at least 32 characters long,
   and set:

        DEMO_SEED_ALLOWED=true

   Keep ENVIRONMENT as development for this local demo. Do not reuse a real
   signing key or copy a real database URL into a document, shell history, or
   source control.

The backend chooses its environment file from DUKAANPULSE_ENV_FILE, defaulting
to .env. Every backend command below explicitly chooses .env.demo.

## 2. Start the demo backend and create an administrator

From backend, create the virtual environment and install the pinned
requirements if it does not already exist:

    .\venv\Scripts\python.exe -m pip install -r requirements.txt
    .\venv\Scripts\python.exe -m pip install -r requirements-dev.txt

Start the isolated backend on port 8001:

    $env:DUKAANPULSE_ENV_FILE = ".env.demo"
    .\venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8001

In a second PowerShell window, also from backend, create the first administrator:

    $env:DUKAANPULSE_ENV_FILE = ".env.demo"
    .\venv\Scripts\python.exe -m app.scripts.create_admin

The script prompts for username, full name, password, and confirmation. The
password must be at least 10 characters. Use a demo-only account.

Before seeding, open http://127.0.0.1:8001/health. It should report healthy
status and demo_seed_allowed as true. Do not proceed if it does not.

## 3. Seed the synthetic scenario

The plan is deterministic by default: seed 42 and 12 months of history. At
least six months are required so both trend windows can be demonstrated.

An optional dry run prints the planned event summary without making network
calls:

    $env:DUKAANPULSE_ENV_FILE = ".env.demo"
    .\venv\Scripts\python.exe -m app.scripts.seed_demo --base-url http://127.0.0.1:8001 --dry-run

Seed the demo:

    $env:DUKAANPULSE_ENV_FILE = ".env.demo"
    .\venv\Scripts\python.exe -m app.scripts.seed_demo --base-url http://127.0.0.1:8001 --months 12 --seed 42

The generator accepts only loopback URLs: localhost, 127.0.0.1, or ::1. It
checks GET /health for demo_seed_allowed=true, requires the exact confirmation
SEED DEMO, prompts for the demo administrator username and password instead of
accepting a password argument, and refuses a target containing products,
customers, suppliers, purchases, or orders. It calls the normal HTTP API, so
the generated records follow the same business rules as UI/API activity.

## 4. Start the demo frontend

From frontend, create another local, ignored environment file:

    Copy-Item .env.example .env.demo

Edit frontend/.env.demo locally so it points to the demo backend and marks the
view clearly:

    VITE_API_BASE_URL=http://127.0.0.1:8001
    VITE_DEMO_BANNER=true

Install and run Vite in demo mode:

    npm.cmd install
    npm.cmd run dev -- --mode demo

Open the local Vite URL shown in the terminal, normally
http://localhost:5173, and sign in with the demo-only administrator. The Cash
& Credit page will show a Demo data banner when VITE_DEMO_BANNER is true.

## 5. Five-minute Cash & Credit walkthrough

Use the Cash & Credit sidebar page. The report is available to ADMIN and
ACCOUNTS; the demo administrator can see it.

| Time | Show | Expected synthetic story |
| ---: | --- | --- |
| 0:00 | The page header, Demo data banner, KPI cards, and aging chart | Explain that the report date is shown as As of and store credit is separate from receivables. |
| 0:40 | Customer risk table sorted by risk score | Show icons plus text for band and trend, then open Details to show returned reasons and inputs. |
| 1:10 | Reliable Retailers | RELIABLE and STABLE. It has six settled invoices with small delays. |
| 1:30 | Chronic Late Stores | RISKY and STABLE, with mostly 30-day-late history plus an open 3,000 invoice 40 days overdue. Use this to show overdue-now and the conservative-series exclusion. |
| 2:00 | Worsening Wholesale | WATCH and WORSENING, with a 1,200 open invoice 20 days overdue. |
| 2:20 | Near Limit Mart | WATCH and STABLE, with a 9,500 open invoice 35 days overdue against a 10,000 credit limit. |
| 2:40 | Newly Opened Shop | INSUFFICIENT_HISTORY: only two settled invoices are planted. Show the explicit lack-of-history explanation instead of a made-up score, trend, or suggestion. |
| 3:05 | Credit Holder Traders | RELIABLE and STABLE. A synthetic completed return creates customer store credit, displayed separately from overdue receivables. |
| 3:30 | Next 5 weeks cash flow | Explain expected IN, expected OUT, cumulative net, and the conservative line. Enter an optional demo opening balance; it changes only the displayed projected balances and is not saved. |
| 4:15 | How this is calculated | Expand the panel to show the API-supplied formulas, thresholds, defaults note, and payment-date data-quality reminder. |
| 4:45 | Band filter and no-access behaviour | Filter to RISKY or INSUFFICIENT_HISTORY. If demonstrating roles, an ADMIN can create an ACCOUNTS user; SALES, WAREHOUSE, and VIEWER do not see Cash & Credit and receive the existing no-access page at a typed URL. |

The actual report date moves with the demo backend's business date, so cash
projection dates and the precise aging snapshot should be read from the page
rather than copied from this script.

## 6. Screenshot checklist

Capture only this synthetic demo environment. Before publishing, verify that
every image has the Demo data banner visible and contains no real account,
customer, supplier, payment, database, token, or browser-network information.

- Cash & Credit overview with KPIs and aging chart.
- Customer risk table with all four band states represented.
- Expanded RISKY customer detail with inputs and reasons.
- INSUFFICIENT_HISTORY detail showing why no score is produced.
- Next 5 weeks projection with an optional opening balance and a negative
  balance indicator, if applicable.
- Expanded methodology panel.
