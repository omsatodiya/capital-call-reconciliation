import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

REQUIRED_COLUMNS = ["date", "description", "amount", "type", "reference"]

DATE_PATTERN = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
AMOUNT_PATTERN = re.compile(r"[+-]?[0-9]+(\.[0-9]{1,2})?")
MAX_AMOUNT = Decimal("999999999999.99")


class RowError(ValueError):
    pass


@dataclass
class ParsedRow:
    date: date
    description: str
    amount: Decimal
    bank_reference: str


def parse_row(row):
    values = {column: (row.get(column) or "").strip() for column in REQUIRED_COLUMNS}

    for column in REQUIRED_COLUMNS:
        if not values[column]:
            raise RowError(f"Missing {column}.")

    transaction_date = parse_date(values["date"])
    amount = parse_amount(values["amount"])
    check_type_matches_sign(values["type"], amount)

    return ParsedRow(
        date=transaction_date,
        description=values["description"],
        amount=amount,
        bank_reference=values["reference"],
    )


def parse_date(value):
    if not DATE_PATTERN.fullmatch(value):
        raise RowError(f"Invalid date '{value}', expected YYYY-MM-DD.")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise RowError(f"'{value}' is not a real calendar date.")


def parse_amount(value):
    cleaned = value.replace(",", "")
    if not AMOUNT_PATTERN.fullmatch(cleaned):
        raise RowError(f"Invalid amount '{value}'.")

    amount = Decimal(cleaned)
    if amount == 0:
        raise RowError("Amount cannot be zero.")
    if abs(amount) > MAX_AMOUNT:
        raise RowError(f"Amount '{value}' is too large.")
    return amount


def check_type_matches_sign(transaction_type, amount):
    transaction_type = transaction_type.lower()
    if transaction_type == "credit":
        if amount < 0:
            raise RowError("Credit amount must be positive.")
    elif transaction_type == "debit":
        if amount > 0:
            raise RowError("Debit amount must be negative.")
    else:
        raise RowError(f"Type must be 'credit' or 'debit', got '{transaction_type}'.")