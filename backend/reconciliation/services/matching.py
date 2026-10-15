from ..models import BankTransaction


def match_transaction(bank_transaction):
    bank_transaction.status = BankTransaction.Status.NEEDS_REVIEW
    bank_transaction.review_reason = "No matching line item found."
    bank_transaction.save(update_fields=["status", "review_reason"])