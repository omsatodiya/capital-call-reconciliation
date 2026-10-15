from django.test import SimpleTestCase

from reconciliation.normalization import (
    contains_words,
    normalize_name,
    normalize_reference,
    normalize_text,
)


class NormalizationTests(SimpleTestCase):
    def test_reference_removes_symbols_and_uppercases(self):
        self.assertEqual(normalize_reference("cc-1003"), "CC1003")
        self.assertEqual(normalize_reference(" CC 1003 "), "CC1003")

    def test_text_collapses_spaces_and_symbols(self):
        self.assertEqual(normalize_text("  wire  incoming, meridian "), "WIRE INCOMING MERIDIAN")

    def test_name_drops_trailing_company_suffix(self):
        self.assertEqual(normalize_name("Meridian Partners LP"), "MERIDIAN PARTNERS")
        self.assertEqual(normalize_name("Haller Capital LLC"), "HALLER CAPITAL")
        self.assertEqual(normalize_name("Acme Ltd."), "ACME")

    def test_name_keeps_trust(self):
        self.assertEqual(normalize_name("Rahul Shah Trust"), "RAHUL SHAH TRUST")

    def test_contains_words_matches_whole_words_only(self):
        self.assertTrue(contains_words("WIRE PATEL FAMILY TRUST", "PATEL FAMILY TRUST"))
        self.assertFalse(contains_words("WIRE XPATEL FAMILY TRUSTEE", "PATEL FAMILY TRUST"))
        self.assertFalse(contains_words("WIRE PATEL", ""))