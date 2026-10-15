from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from reconciliation.models import BankTransaction, Organization

HEADER = "date,description,amount,type,reference\n"


class ImportTests(TestCase):
    def setUp(self):
        self.northwind = Organization.objects.create(slug="northwind", name="Northwind Ventures")
        self.bluebird = Organization.objects.create(slug="bluebird", name="Bluebird Capital")
        self.client = APIClient()

    def upload(self, content, org="northwind"):
        file = SimpleUploadedFile("statement.csv", content.encode("utf-8"), content_type="text/csv")
        return self.client.post(
            "/api/imports/",
            {"file": file},
            format="multipart",
            headers={"X-Organization": org},
        )

    def test_missing_column_rejects_file_and_saves_nothing(self):
        content = "date,description,amount,type\n2026-04-03,WIRE IN,100.00,credit\n"
        response = self.upload(content)

        self.assertEqual(response.status_code, 400)
        self.assertIn("reference", response.json()["detail"])
        self.assertEqual(BankTransaction.objects.count(), 0)

    def test_invalid_rows_are_reported_and_valid_rows_imported(self):
        content = HEADER + (
            "2026-04-03,WIRE IN,100.00,credit,FT1\n"
            "2026-04-31,WIRE IN,100.00,credit,FT2\n"
            "2026-04-05,WIRE IN,-100.00,credit,FT3\n"
            "2026-04-06,WIRE IN,200.00,credit,FT4\n"
        )
        response = self.upload(content)

        body = response.json()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(body["imported"], 2)
        self.assertEqual([error["line"] for error in body["errors"]], [3, 4])

    def test_amount_is_stored_as_decimal(self):
        self.upload(HEADER + '2026-04-03,WIRE IN,"25,000.00",credit,FT1\n')

        stored = BankTransaction.objects.get(bank_reference="FT1")
        self.assertIsInstance(stored.amount, Decimal)
        self.assertEqual(stored.amount, Decimal("25000.00"))

    def test_debit_is_stored_as_ignored(self):
        self.upload(HEADER + "2026-04-05,BANK FEE,-25.00,debit,FEE1\n")

        stored = BankTransaction.objects.get(bank_reference="FEE1")
        self.assertEqual(stored.status, BankTransaction.Status.IGNORED)

    def test_duplicate_inside_same_file_is_skipped(self):
        content = HEADER + (
            "2026-04-03,WIRE IN,100.00,credit,FT1\n"
            "2026-04-03,WIRE IN,100.00,credit,FT1\n"
        )
        body = self.upload(content).json()

        self.assertEqual(body["imported"], 1)
        self.assertEqual(body["duplicates"], 1)
        self.assertEqual(body["duplicate_rows"][0]["line"], 3)
        self.assertEqual(BankTransaction.objects.count(), 1)

    def test_reupload_skips_everything_as_duplicates(self):
        content = HEADER + (
            "2026-04-03,WIRE IN,100.00,credit,FT1\n"
            "2026-04-04,WIRE IN,200.00,credit,FT2\n"
        )
        self.upload(content)
        body = self.upload(content).json()

        self.assertEqual(body["imported"], 0)
        self.assertEqual(body["duplicates"], 2)
        self.assertEqual(BankTransaction.objects.count(), 2)

    def test_same_reference_is_allowed_in_another_organization(self):
        content = HEADER + "2026-04-03,WIRE IN,100.00,credit,FT1\n"
        self.upload(content, org="northwind")
        body = self.upload(content, org="bluebird").json()

        self.assertEqual(body["imported"], 1)
        self.assertEqual(BankTransaction.objects.filter(bank_reference="FT1").count(), 2)