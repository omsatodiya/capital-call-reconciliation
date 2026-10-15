from django.db import transaction

from ..models import BankTransaction, LineItem, Match


class ActionConflict(Exception):
    pass

def get_match(organization, match_id):
    return Match.objects.select_related("bank_transaction", "line_item").get(
        pk=match_id, bank_transaction__organization=organization
    )

@transaction.atomic

def approve_match(organization, match_id):
    match = get_match(organization, match_id)

    # Lock order is always transaction first, then line item, to avoid deadlocks.
    bank_transaction = lock_transaction(match.bank_transaction.pk)
    line_item = LineItem.objects.select_for_update().get(pk=match.line_item.pk)
    match.refresh_from_db()

    if bank_transaction.status == BankTransaction.Status.RECONCILED:
        raise ActionConflict("This transaction is already reconciled.")
    if match.status != Match.Status.PROPOSED:
        raise ActionConflict("Only proposed matches can be approved.")

    amount = bank_transaction.amount
    remaining = line_item.amount_remaining
    if amount > remaining:
        raise ActionConflict(
            f"Amount {amount:,.2f} is more than the remaining {remaining:,.2f}."
        )

    line_item.amount_funded += amount
    if line_item.amount_remaining == 0:
        line_item.status = LineItem.Status.FUNDED
    else:
        line_item.status = LineItem.Status.PARTIALLY_FUNDED
    line_item.save(update_fields=["amount_funded", "status"])

    match.status = Match.Status.APPROVED
    match.save(update_fields=["status"])
    Match.objects.filter(bank_transaction=bank_transaction).exclude(pk=match.pk).update(
        status=Match.Status.REJECTED
    )

    bank_transaction.status = BankTransaction.Status.RECONCILED
    bank_transaction.save(update_fields=["status"])
    return bank_transaction


@transaction.atomic
def reject_match(organization, match_id):
    match = get_match(organization, match_id)
    bank_transaction = lock_transaction(match.bank_transaction.pk)
    match.refresh_from_db()

    if match.status != Match.Status.PROPOSED:
        raise ActionConflict("Only proposed matches can be rejected.")

    match.status = Match.Status.REJECTED
    match.save(update_fields=["status"])

    has_proposed = Match.objects.filter(
        bank_transaction=bank_transaction, status=Match.Status.PROPOSED
    ).exists()
    if not has_proposed:
        bank_transaction.status = BankTransaction.Status.NEEDS_REVIEW
        bank_transaction.review_reason = "All suggested matches were rejected."
        bank_transaction.save(update_fields=["status", "review_reason"])
    return bank_transaction


@transaction.atomic
def ignore_transaction(organization, transaction_id):
    bank_transaction = BankTransaction.objects.select_for_update().get(
        pk=transaction_id, organization=organization
    )

    if bank_transaction.status == BankTransaction.Status.RECONCILED:
        raise ActionConflict("A reconciled transaction cannot be ignored.")
    if bank_transaction.status == BankTransaction.Status.IGNORED:
        raise ActionConflict("This transaction is already ignored.")

    bank_transaction.status = BankTransaction.Status.IGNORED
    bank_transaction.save(update_fields=["status"])
    Match.objects.filter(
        bank_transaction=bank_transaction, status=Match.Status.PROPOSED
    ).update(status=Match.Status.REJECTED)
    return bank_transaction


def lock_transaction(transaction_id):
    return BankTransaction.objects.select_for_update().get(pk=transaction_id)