from datetime import date
from decimal import Decimal
from io import StringIO
from itertools import count

from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from reconciliation.models import BankTransaction, LineItem, Match, Organization
from reconciliation.services.matching import match_transaction

reference_numbers = count(1)


class ActionTests(TestCase):
    def setUp(self):
        call_command("seed_demo", stdout=StringIO())
        self.northwind = Organization.objects.get(slug="northwind")
        self.client = APIClient()

    def credit(self, description, amount, org=None):
        payment = BankTransaction.objects.create(
            organization=org or self.northwind,
            date=date(2026, 4, 12),
            description=description,
            amount=Decimal(amount),
            bank_reference=f"FT{next(reference_numbers)}",
            status=BankTransaction.Status.NEEDS_REVIEW,
        )
        match_transaction(payment)
        payment.refresh_from_db()
        return payment

    def proposed_match(self, payment, reference=None):
        matches = Match.objects.filter(bank_transaction=payment, status=Match.Status.PROPOSED)
        if reference:
            matches = matches.filter(line_item__expected_reference=reference)
        return matches.get()

    def post(self, url, org="northwind"):
        return self.client.post(url, headers={"X-Organization": org})

    def line_item(self, reference):
        return LineItem.objects.get(expected_reference=reference)

    # Approve

    def test_approve_updates_funding_and_reconciles(self):
        payment = self.credit("WIRE INCOMING PATEL FAMILY TRUST", "12500.00")
        match = self.proposed_match(payment)

        response = self.post(f"/api/matches/{match.pk}/approve/")

        self.assertEqual(response.status_code, 200)
        item = self.line_item("CC-1003")
        self.assertEqual(item.amount_funded, Decimal("12500.00"))
        self.assertEqual(item.status, LineItem.Status.FUNDED)
        payment.refresh_from_db()
        self.assertEqual(payment.status, BankTransaction.Status.RECONCILED)

    def test_partial_approval_marks_line_item_partially_funded(self):
        payment = self.credit("ACH CREDIT HALLER CAPITAL LLC CC-1001", "20000.00")
        self.post(f"/api/matches/{self.proposed_match(payment).pk}/approve/")

        item = self.line_item("CC-1001")
        self.assertEqual(item.amount_funded, Decimal("20000.00"))
        self.assertEqual(item.status, LineItem.Status.PARTIALLY_FUNDED)
        self.assertEqual(item.amount_remaining, Decimal("7500.00"))

    def test_second_approval_returns_409_without_double_funding(self):
        payment = self.credit("WIRE INCOMING PATEL FAMILY TRUST", "12500.00")
        url = f"/api/matches/{self.proposed_match(payment).pk}/approve/"

        first = self.post(url)
        second = self.post(url)

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 409)
        self.assertEqual(self.line_item("CC-1003").amount_funded, Decimal("12500.00"))

    def test_approve_rechecks_remaining_amount(self):
        first = self.credit("HALLER CAPITAL CC-1001", "20000.00")
        second = self.credit("HALLER CAPITAL CC-1001 AGAIN", "20000.00")

        self.post(f"/api/matches/{self.proposed_match(first).pk}/approve/")
        response = self.post(f"/api/matches/{self.proposed_match(second).pk}/approve/")

        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.line_item("CC-1001").amount_funded, Decimal("20000.00"))

    def test_approving_one_candidate_rejects_the_others(self):
        payment = self.credit("WIRE INCOMING OAKRIDGE HOLDINGS LLC", "15000.00")
        chosen = self.proposed_match(payment, "CC-1005")

        self.post(f"/api/matches/{chosen.pk}/approve/")

        other = Match.objects.get(bank_transaction=payment, line_item__expected_reference="CC-1006")
        self.assertEqual(other.status, Match.Status.REJECTED)
        self.assertEqual(self.line_item("CC-1006").amount_funded, Decimal("0.00"))

    # Reject and ignore

    def test_rejecting_last_proposed_match_moves_to_needs_review(self):
        payment = self.credit("WIRE INCOMING PATEL FAMILY TRUST", "12500.00")
        response = self.post(f"/api/matches/{self.proposed_match(payment).pk}/reject/")

        self.assertEqual(response.status_code, 200)
        payment.refresh_from_db()
        self.assertEqual(payment.status, BankTransaction.Status.NEEDS_REVIEW)
        self.assertTrue(payment.review_reason)

    def test_ignore_rejects_proposed_matches(self):
        payment = self.credit("WIRE INCOMING PATEL FAMILY TRUST", "12500.00")
        response = self.post(f"/api/transactions/{payment.pk}/ignore/")

        self.assertEqual(response.status_code, 200)
        payment.refresh_from_db()
        self.assertEqual(payment.status, BankTransaction.Status.IGNORED)
        self.assertFalse(
            Match.objects.filter(bank_transaction=payment, status=Match.Status.PROPOSED).exists()
        )

    def test_ignoring_reconciled_transaction_returns_409(self):
        payment = self.credit("WIRE INCOMING PATEL FAMILY TRUST", "12500.00")
        self.post(f"/api/matches/{self.proposed_match(payment).pk}/approve/")

        response = self.post(f"/api/transactions/{payment.pk}/ignore/")
        self.assertEqual(response.status_code, 409)

    # Organization isolation

    def test_transaction_list_only_shows_own_organization(self):
        self.credit("WIRE INCOMING PATEL FAMILY TRUST", "12500.00")

        response = self.client.get("/api/transactions/", headers={"X-Organization": "bluebird"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_approving_another_organizations_match_returns_404(self):
        payment = self.credit("WIRE INCOMING PATEL FAMILY TRUST", "12500.00")
        match = self.proposed_match(payment)

        response = self.post(f"/api/matches/{match.pk}/approve/", org="bluebird")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.line_item("CC-1003").amount_funded, Decimal("0.00"))
        match.refresh_from_db()
        self.assertEqual(match.status, Match.Status.PROPOSED)

    def test_ignoring_another_organizations_transaction_returns_404(self):
        payment = self.credit("WIRE INCOMING PATEL FAMILY TRUST", "12500.00")
        response = self.post(f"/api/transactions/{payment.pk}/ignore/", org="bluebird")
        self.assertEqual(response.status_code, 404)

    def test_missing_header_returns_400(self):
        response = self.client.get("/api/transactions/")
        self.assertEqual(response.status_code, 400)