import csv
import io

from django.db import IntegrityError, transaction

from ..models import BankTransaction
from ..parsing import REQUIRED_COLUMNS, RowError, parse_row
from .matching import match_transaction


class ImportFileError(Exception):
    pass


@transaction.atomic
def import_bank_statement(organization, uploaded_file):
    reader = read_csv(uploaded_file)

    header = next(reader, None)
    if header is None:
        raise ImportFileError("The file is empty.")

    header = [column.strip().lower() for column in header]
    missing = [column for column in REQUIRED_COLUMNS if column not in header]
    if missing:
        raise ImportFileError(f"Missing columns: {', '.join(missing)}.")

    imported = 0
    duplicates = []
    errors = []
    seen_references = set()

    for line_number, cells in enumerate(reader, start=2):
        if not any(cell.strip() for cell in cells):
            continue

        try:
            parsed = parse_row(dict(zip(header, cells)))
        except RowError as error:
            errors.append({"line": line_number, "message": str(error)})
            continue

        if parsed.bank_reference in seen_references:
            duplicates.append({"line": line_number, "reference": parsed.bank_reference})
            continue
        seen_references.add(parsed.bank_reference)

        bank_transaction = save_transaction(organization, parsed)
        if bank_transaction is None:
            duplicates.append({"line": line_number, "reference": parsed.bank_reference})
            continue

        imported += 1
        if bank_transaction.is_credit:
            match_transaction(bank_transaction)

    return {
        "imported": imported,
        "duplicates": len(duplicates),
        "duplicate_rows": duplicates,
        "errors": errors,
    }


def read_csv(uploaded_file):
    try:
        text = uploaded_file.read().decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ImportFileError("The file must be a UTF-8 encoded CSV.")
    return csv.reader(io.StringIO(text))


def save_transaction(organization, parsed):
    if parsed.amount > 0:
        status = BankTransaction.Status.NEEDS_REVIEW
    else:
        status = BankTransaction.Status.IGNORED

    try:
        with transaction.atomic():
            return BankTransaction.objects.create(
                organization=organization,
                date=parsed.date,
                description=parsed.description,
                amount=parsed.amount,
                bank_reference=parsed.bank_reference,
                status=status,
            )
    except IntegrityError:
        return None