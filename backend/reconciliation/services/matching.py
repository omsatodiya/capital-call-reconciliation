from django.db.models import F

from ..models import BankTransaction, LineItem, Match
from ..normalization import (
    contains_words,
    normalize_name,
    normalize_reference,
    normalize_text,
)


def match_transaction(bank_transaction):
    candidates = list(eligible_line_items(bank_transaction))

    by_reference = find_by_reference(bank_transaction, candidates)
    if by_reference:
        apply_reference_matches(bank_transaction, by_reference)
    else:
        by_name = find_by_name_and_amount(bank_transaction, candidates)
        apply_name_matches(bank_transaction, by_name)


def eligible_line_items(bank_transaction):
    return LineItem.objects.filter(
        organization=bank_transaction.organization,
        amount_funded__lt=F("amount_called"),
        capital_call__call_date__lte=bank_transaction.date,
    ).select_related("investor", "capital_call")


def find_by_reference(bank_transaction, candidates):
    searchable = (
        normalize_reference(bank_transaction.description),
        normalize_reference(bank_transaction.bank_reference),
    )
    return [
        item
        for item in candidates
        if any(normalize_reference(item.expected_reference) in text for text in searchable)
    ]


def find_by_name_and_amount(bank_transaction, candidates):
    description = normalize_text(bank_transaction.description)
    return [
        item
        for item in candidates
        if bank_transaction.amount == item.amount_remaining
        and contains_words(description, normalize_name(item.investor.name))
    ]


def apply_reference_matches(bank_transaction, items):
    amount = bank_transaction.amount

    if len(items) > 1:
        for item in items:
            propose(bank_transaction, item, f"Reference {item.expected_reference} found.")
        references = ", ".join(item.expected_reference for item in items)
        set_status(
            bank_transaction,
            BankTransaction.Status.NEEDS_REVIEW,
            f"Several references found: {references}.",
        )
        return

    item = items[0]
    remaining = item.amount_remaining

    if amount > remaining:
        set_status(
            bank_transaction,
            BankTransaction.Status.NEEDS_REVIEW,
            f"Reference {item.expected_reference} found, but amount {money(amount)} "
            f"is more than remaining {money(remaining)} (overpayment).",
        )
        return

    if amount == remaining:
        detail = f"amount equals remaining {money(remaining)}"
    else:
        detail = f"partial payment of {money(amount)} against remaining {money(remaining)}"
    propose(bank_transaction, item, f"Reference {item.expected_reference} found; {detail}.")
    set_status(bank_transaction, BankTransaction.Status.SUGGESTED)


def apply_name_matches(bank_transaction, items):
    if not items:
        set_status(
            bank_transaction,
            BankTransaction.Status.NEEDS_REVIEW,
            "No reference found, and no investor name with a matching remaining amount.",
        )
        return

    for item in items:
        propose(
            bank_transaction,
            item,
            f"Name {item.investor.name} found; amount equals remaining "
            f"{money(item.amount_remaining)}.",
        )

    if len(items) == 1:
        set_status(bank_transaction, BankTransaction.Status.SUGGESTED)
    else:
        references = ", ".join(item.expected_reference for item in items)
        set_status(
            bank_transaction,
            BankTransaction.Status.NEEDS_REVIEW,
            f"Name and amount match several line items: {references}.",
        )


def propose(bank_transaction, line_item, reason):
    Match.objects.create(bank_transaction=bank_transaction, line_item=line_item, reason=reason)


def set_status(bank_transaction, status, review_reason=""):
    bank_transaction.status = status
    bank_transaction.review_reason = review_reason
    bank_transaction.save(update_fields=["status", "review_reason"])


def money(amount):
    return f"{amount:,.2f}"