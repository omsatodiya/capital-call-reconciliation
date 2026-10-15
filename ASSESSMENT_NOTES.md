# Callwise

Bank reconciliation for capital calls. A GP uploads a bank statement CSV,
the app suggests which capital call line item each incoming payment belongs
to (with a reason), and the GP approves, rejects or ignores each suggestion.

**Stack:** Django 5.2 + Django REST Framework, PostgreSQL 16, React (Vite).

## Setup from a fresh clone

Requirements: Python 3.11+, Node 20.19+, Docker.

```bash
git clone <repo-url>
cd capital-call-reconciliation

# 1. Environment and database
cp .env.example .env            # Windows: copy .env.example .env
docker compose up -d

# 2. Backend
cd backend
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver

# 3. Frontend (second terminal)
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The Vite dev server proxies `/api` to Django on
port 8000, so no CORS setup is needed.

A sample statement is in `sample_data/sample_bank_statement.csv`.

## Running the tests

From `backend/` with the virtual environment active (Postgres must be running):

```bash
python manage.py test reconciliation
```

## Data model

- **Organization**: a GP firm (tenant). Identified by `slug`.
- **InvestorEntity**: the legal entity an LP invests through. Unique name per organization.
- **CapitalCall**: call number, call date, due date. Unique number per organization.
- **LineItem**: one investor's share of one call. Expected reference (unique per
  organization), amount called, amount funded, status. Remaining is computed,
  not stored. Database check constraints keep `0 <= funded <= called`.
- **BankTransaction**: one imported bank row. Unique bank reference per
  organization. Status: `suggested`, `needs_review`, `reconciled`, `ignored`.
  `review_reason` explains every `needs_review`.
- **Match**: a proposed link from a transaction to a line item, with a reason.
  Status: `proposed`, `approved`, `rejected`. A partial unique constraint
  allows at most one approved match per transaction.

All amounts are `DecimalField(max_digits=14, decimal_places=2)` and are
parsed from strings, never floats.

## API

Every endpoint except the organization list requires the
`X-Organization: <slug>` header. Missing header: `400`. Unknown organization
or a record from another organization: `404`.

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/organizations/` | List organizations (for the switcher) |
| GET | `/api/line-items/` | Line items with called, funded, remaining, status |
| GET | `/api/transactions/` | Transactions, newest first, with matches and reasons |
| POST | `/api/imports/` | Upload CSV (`multipart/form-data`, field `file`). Returns the import summary |
| POST | `/api/matches/<id>/approve/` | Approve a proposed match. `409` if no longer valid |
| POST | `/api/matches/<id>/reject/` | Reject a proposed match |
| POST | `/api/transactions/<id>/ignore/` | Ignore a transaction. `409` if reconciled |

Import summary: `{"imported", "duplicates", "duplicate_rows", "errors"}`,
where each error has `line` and `message`.

## Code layout

- `reconciliation/parsing.py`: validates one CSV row (pure function).
- `reconciliation/normalization.py`: reference and name normalisation (pure).
- `reconciliation/services/imports.py`: file-level import, duplicates.
- `reconciliation/services/matching.py`: the matching rules.
- `reconciliation/services/actions.py`: approve, reject, ignore.
- `reconciliation/mixins.py`: resolves the organization from the header.
- Views only handle HTTP and call services.

## How double funding is prevented

Approve runs in one database transaction and locks the bank transaction row,
then the line item row (`select_for_update`, always in that order to avoid
deadlocks). After locking it re-reads the current state, so a second,
simultaneous approval waits, then sees `reconciled` and gets `409`. The amount
is re-checked against the line item's current remaining amount. Database
constraints (`funded <= called`, one approved match per transaction) are a
final safety net.

## Assumptions

- The `X-Organization` value is trimmed and lowercased before lookup.
- CSV header names are trimmed and case-insensitive. Extra columns are ignored.
- Files must be UTF-8 (a byte-order mark from Excel is handled).
- Line numbers count physical lines with the header as line 1. Blank lines are
  skipped but still counted. A quoted field containing a newline would shift
  later line numbers.
- Amounts: thousands separators are removed without checking their positions;
  at most two decimal places; formats like `1e3`, `NaN` or `$100` are rejected.
- Bank references are compared exactly after trimming (case-sensitive).
- A row is only counted as a duplicate if it is otherwise valid; invalid rows
  are reported as errors.
- The reference check is a substring check on normalised text, as the spec
  describes. This means `CC1001` would also be found inside `CC10015`.
- The reference check only searches eligible line items. A reference to an
  ineligible line item (fully funded, other organization, call date after the
  payment) counts as not found, so the name and amount check runs.
- Suggestions use each line item's remaining amount at import time. Two
  pending suggestions can point at the same line item; approval re-checks the
  amount, so the second gets `409` if it no longer fits.
- When several references are found, all are proposed regardless of amount;
  approval re-checks.
- Ignoring an already ignored transaction returns `409`.
- Rejecting the last proposed match moves the transaction to `needs_review`
  with the reason "All suggested matches were rejected."
- Re-running `seed_demo` never overwrites existing line items, so it cannot
  wipe funded amounts.
- The organization list endpoint is not scoped, because the switcher needs it
  before an organization is chosen. It exposes only slugs and names.
- Amounts are displayed as USD (the spec does not name a currency).

## Trade-offs

- `LineItem` stores `organization` directly, duplicating `capital_call.organization`,
  to make scoping simple and to enforce a unique reference per organization.
- The CSV `type` column is not stored; the amount's sign carries the same information.
- Matching runs one eligibility query per credit. Fine for a few thousand rows.
- The dev proxy avoids CORS locally. Production would serve both apps from one
  domain or configure CORS.

## Next steps

- A threaded test for truly simultaneous approvals (current tests cover the
  sequential case; the locking is what handles concurrency).
- Load eligible line items once per import instead of once per credit.
- Cancel stale requests in the frontend when switching organization quickly.
- Pagination for large transaction lists.
- Airtable sync for `needs_review` transactions (optional bonus, not done).

## Integrity

I used Claude for limited assistance during the initial project setup and to understand some code syntax and implementation details. Since the assessment required setting up the project from scratch, I used AI to clarify the initial setup steps, understand how certain components and configurations fit together, and resolve doubts about syntax while working through the implementation. I referred to AI explanations as a supplementary learning resource rather than relying solely on them, as I found it helpful for getting quick, context-specific explanations while building the project. I acknowledge that the assessment instructions explicitly prohibit AI assistance, including for project setup and code-related guidance.