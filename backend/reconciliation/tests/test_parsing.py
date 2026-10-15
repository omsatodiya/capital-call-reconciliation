from datetime import date
from decimal import Decimal

from django.test import SimpleTestCase

from reconciliation.parsing import RowError, parse_row


def make_row(**overrides):
    row = {
        "date": "2026-04-03",
        "description": "WIRE INCOMING PATEL FAMILY TRUST",
        "amount": "12500.00",
        "type": "credit",
        "reference": "FT1",
    }
    row.update(overrides)
    return row


class ParseRowTests(SimpleTestCase):
    def test_valid_row(self):
        parsed = parse_row(make_row())
        self.assertEqual(parsed.date, date(2026, 4, 3))
        self.assertEqual(parsed.amount, Decimal("12500.00"))
        self.assertEqual(parsed.bank_reference, "FT1")

    def test_amount_with_thousands_separator_is_decimal(self):
        parsed = parse_row(make_row(amount="25,000.00"))
        self.assertIsInstance(parsed.amount, Decimal)
        self.assertEqual(parsed.amount, Decimal("25000.00"))

    def test_fields_are_trimmed(self):
        parsed = parse_row(make_row(description="  wire in  ", reference=" FT1 "))
        self.assertEqual(parsed.description, "wire in")
        self.assertEqual(parsed.bank_reference, "FT1")

    def test_type_is_case_insensitive(self):
        parsed = parse_row(make_row(type="CREDIT"))
        self.assertEqual(parsed.amount, Decimal("12500.00"))

    def test_debit_with_negative_amount(self):
        parsed = parse_row(make_row(amount="-25.00", type="debit"))
        self.assertEqual(parsed.amount, Decimal("-25.00"))

    def test_credit_with_negative_amount_is_rejected(self):
        with self.assertRaisesMessage(RowError, "Credit amount must be positive"):
            parse_row(make_row(amount="-15000.00"))

    def test_debit_with_positive_amount_is_rejected(self):
        with self.assertRaisesMessage(RowError, "Debit amount must be negative"):
            parse_row(make_row(amount="25.00", type="debit"))

    def test_zero_amount_is_rejected(self):
        with self.assertRaises(RowError):
            parse_row(make_row(amount="0.00"))

    def test_non_numeric_amount_is_rejected(self):
        for bad in ["abc", "1e3", "NaN", "12.345", "$100"]:
            with self.subTest(amount=bad):
                with self.assertRaises(RowError):
                    parse_row(make_row(amount=bad))

    def test_impossible_date_is_rejected(self):
        with self.assertRaisesMessage(RowError, "not a real calendar date"):
            parse_row(make_row(date="2026-04-31"))

    def test_wrong_date_format_is_rejected(self):
        for bad in ["03/04/2026", "20260403", "2026-4-3"]:
            with self.subTest(date=bad):
                with self.assertRaises(RowError):
                    parse_row(make_row(date=bad))

    def test_unknown_type_is_rejected(self):
        with self.assertRaises(RowError):
            parse_row(make_row(type="transfer"))

    def test_missing_description_is_rejected(self):
        with self.assertRaisesMessage(RowError, "Missing description"):
            parse_row(make_row(description="   "))

    def test_missing_reference_is_rejected(self):
        with self.assertRaisesMessage(RowError, "Missing reference"):
            parse_row(make_row(reference=""))