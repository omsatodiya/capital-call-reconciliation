from datetime import date
from decimal import Decimal
from io import StringIO
from itertools import count

from django.core.management import call_command
from django.test import TestCase

from reconciliation.models import BankTransaction, LineItem, Match, Organization
from reconciliation.services.matching import match_transaction

reference_numbers = count(1)


class MatchingTests(TestCase):
    def setUp(self):
        call_command("seed_demo", stdout=StringIO())
        self.northwind = Organization.objects.get(slug="northwind")

    def credit(self, description, amount, on=date(2026, 4, 12), bank_reference=None):
        payment = BankTransaction.objects.create(
            organization=self.northwind,
            date=on,
            description=description,
            amount=Decimal(amount),
            bank_reference=bank_reference or f"FT{next(reference_numbers)}",
            status=BankTransaction.Status.NEEDS_REVIEW,
        )
        match_transaction(payment)
        payment.refresh_from_db()
        return payment

    def matches_for(self, payment):
        return Match.objects.filter(bank_transaction=payment)

    def matched_references(self, payment):
        return sorted(m.line_item.expected_reference for m in self.matches_for(payment))

    # Reference check

    def test_reference_match_is_suggested(self):
        payment = self.credit("WIRE INCOMING RAHUL SHAH TRUST REF CC-1002", "25000.00")
        self.assertEqual(payment.status, BankTransaction.Status.SUGGESTED)
        self.assertEqual(self.matched_references(payment), ["CC-1002"])

    def test_lowercase_reference_without_dash_matches(self):
        payment = self.credit("ACH CREDIT HALLER CAPITAL cc1001", "27500.00")
        self.assertEqual(payment.status, BankTransaction.Status.SUGGESTED)
        self.assertEqual(self.matched_references(payment), ["CC-1001"])

    def test_partial_payment_is_suggested(self):
        payment = self.credit("ACH CREDIT HALLER CAPITAL LLC CC-1001", "20000.00")
        self.assertEqual(payment.status, BankTransaction.Status.SUGGESTED)
        self.assertIn("partial payment", self.matches_for(payment).get().reason)

    def test_reference_in_bank_reference_field_matches(self):
        payment = self.credit("INCOMING WIRE", "12500.00", bank_reference="CC1003-X")
        self.assertEqual(self.matched_references(payment), ["CC-1003"])

    def test_overpayment_needs_review_with_no_match(self):
        payment = self.credit("WIRE INCOMING PATEL FAMILY TRUST CC-1003", "13000.00")
        self.assertEqual(payment.status, BankTransaction.Status.NEEDS_REVIEW)
        self.assertEqual(self.matches_for(payment).count(), 0)
        self.assertIn("overpayment", payment.review_reason)

    def test_several_references_propose_all_and_need_review(self):
        payment = self.credit("WIRE CC-1002 AND CC-1003", "10000.00")
        self.assertEqual(payment.status, BankTransaction.Status.NEEDS_REVIEW)
        self.assertEqual(self.matched_references(payment), ["CC-1002", "CC-1003"])

    def test_reference_from_another_organization_is_not_matched(self):
        payment = self.credit("WIRE INCOMING CEDAR GROVE FUND CC-2001", "40000.00")
        self.assertEqual(payment.status, BankTransaction.Status.NEEDS_REVIEW)
        self.assertEqual(self.matches_for(payment).count(), 0)

    def test_payment_before_call_date_is_not_matched(self):
        payment = self.credit(
            "WIRE INCOMING OAKRIDGE HOLDINGS LLC REF CC-1006",
            "15000.00",
            on=date(2026, 3, 20),
        )
        self.assertEqual(payment.status, BankTransaction.Status.NEEDS_REVIEW)
        self.assertEqual(self.matches_for(payment).count(), 0)

    def test_fully_funded_line_item_is_not_eligible(self):
        LineItem.objects.filter(expected_reference="CC-1002").update(
            amount_funded=Decimal("25000.00")
        )
        payment = self.credit("WIRE INCOMING RAHUL SHAH TRUST REF CC-1002", "25000.00")
        self.assertEqual(self.matches_for(payment).count(), 0)

    # Name and amount check

    def test_name_and_amount_match_is_suggested(self):
        payment = self.credit("WIRE INCOMING PATEL FAMILY TRUST", "12500.00")
        self.assertEqual(payment.status, BankTransaction.Status.SUGGESTED)
        self.assertEqual(self.matched_references(payment), ["CC-1003"])

    def test_name_match_ignores_company_suffix_and_case(self):
        payment = self.credit("  wire incoming meridian partners  ", "15000.00")
        self.assertEqual(self.matched_references(payment), ["CC-1004"])

    def test_name_with_different_amount_is_not_matched(self):
        payment = self.credit("WIRE INCOMING PATEL FAMILY TRUST", "12000.00")
        self.assertEqual(payment.status, BankTransaction.Status.NEEDS_REVIEW)
        self.assertEqual(self.matches_for(payment).count(), 0)

    def test_name_and_amount_with_several_candidates_needs_review(self):
        payment = self.credit("WIRE INCOMING OAKRIDGE HOLDINGS LLC", "15000.00")
        self.assertEqual(payment.status, BankTransaction.Status.NEEDS_REVIEW)
        self.assertEqual(self.matched_references(payment), ["CC-1005", "CC-1006"])

    def test_name_must_match_whole_words(self):
        payment = self.credit("WIRE FROM XPATEL FAMILY TRUSTEE", "12500.00")
        self.assertEqual(self.matches_for(payment).count(), 0)

    def test_unknown_payment_needs_review_with_reason(self):
        payment = self.credit("UNKNOWN INCOMING WIRE", "9999.99")
        self.assertEqual(payment.status, BankTransaction.Status.NEEDS_REVIEW)
        self.assertEqual(self.matches_for(payment).count(), 0)
        self.assertTrue(payment.review_reason)