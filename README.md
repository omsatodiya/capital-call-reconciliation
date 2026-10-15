# Callwise

A small fund administration tool for matching incoming bank payments to capital
call line items.

When a fund issues a capital call, each investor wires their share, but bank
descriptions are messy: references get dropped or mistyped, payments arrive in
parts, and sometimes too much is sent. This app imports a bank statement,
suggests which line item each payment belongs to and explains why, and lets
the GP approve, reject or ignore each suggestion. Approved payments update how
much each investor has paid.

Built with Django REST Framework, PostgreSQL and React.

## Features

- CSV import from the browser, with per-line validation errors and duplicate detection
- Matching by payment reference (including partial payments and overpayments),
  then by investor name and exact amount
- A plain-language reason for every suggestion and every item needing review
- Approve, reject and ignore, with approvals that can never fund a line item twice
- Multiple organizations with fully separated data

## Quick start

Requirements: Python 3.11+, Node 20.19+, Docker.

```bash
cp .env.example .env
docker compose up -d

cd backend
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173, pick an organization and upload
`sample_data/sample_bank_statement.csv`.

## Tests

```bash
cd backend
python manage.py test reconciliation
```

## How matching works

For each incoming payment, only line items in the same organization that still
have money owed and whose capital call was sent on or before the payment date
are considered.

1. **Reference.** If a line item's reference (like `CC-1003`, also written as
   `cc1003`) appears in the description or bank reference, it is suggested,
   unless the payment is larger than what is still owed, which is flagged for
   review as an overpayment.
2. **Name and amount.** Otherwise, a line item is suggested if the investor's
   name appears in the description and the amount exactly equals what is still owed.

Anything ambiguous or unmatched is marked `needs_review` with a reason.

## Project structure

```
backend/
  config/                    Django settings and root URLs
  reconciliation/
    models.py                Organizations, capital calls, line items, transactions, matches
    parsing.py               CSV row validation
    normalization.py         Reference and name normalisation
    services/                Import, matching and approve/reject/ignore logic
    views.py, serializers.py The REST API
    management/commands/     seed_demo
    tests/
frontend/
  src/
    api.js                   API client (sets the organization header)
    components/              Upload form, transaction table, line item panel
sample_data/                 Example bank statement
```

## More detail

See [ASSESSMENT_NOTES.md](ASSESSMENT_NOTES.md) for the data model, API
endpoints, how double funding is prevented, assumptions and next steps.