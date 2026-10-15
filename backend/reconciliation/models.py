from django.db import models
from decimal import Decimal
from django.db.models import F, Q

class Organization(models.Model):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name



class InvestorEntity(models.Model):
    organization = models.ForeignKey(
        Organization, on_delete=models.PROTECT, related_name="investors"
    )
    name = models.CharField(max_length=200)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "name"], name="unique_investor_per_org"
            ),
        ]

    def __str__(self):
        return self.name


class CapitalCall(models.Model):
    organization = models.ForeignKey(
        Organization, on_delete=models.PROTECT, related_name="capital_calls"
    )
    number = models.PositiveIntegerField()
    call_date = models.DateField()
    due_date = models.DateField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "number"], name="unique_call_number_per_org"
            ),
        ]

    def __str__(self):
        return f"Capital call #{self.number}"


class LineItem(models.Model):
    class Status(models.TextChoices):
        OPEN = "open"
        PARTIALLY_FUNDED = "partially_funded"
        FUNDED = "funded"

    organization = models.ForeignKey(
        Organization, on_delete=models.PROTECT, related_name="line_items"
    )
    capital_call = models.ForeignKey(
        CapitalCall, on_delete=models.PROTECT, related_name="line_items"
    )
    investor = models.ForeignKey(
        InvestorEntity, on_delete=models.PROTECT, related_name="line_items"
    )
    expected_reference = models.CharField(max_length=50)
    amount_called = models.DecimalField(max_digits=14, decimal_places=2)
    from decimal import Decimal
    amount_funded = models.DecimalField(max_digits=14,decimal_places=2,default=Decimal("0.00"))
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.OPEN
    )

    class Meta:
        ordering = ["expected_reference"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "expected_reference"],
                name="unique_reference_per_org",
            ),
            models.UniqueConstraint(
                fields=["capital_call", "investor"],
                name="unique_investor_per_call",
            ),
            models.CheckConstraint(
                condition=Q(amount_called__gt=0), name="amount_called_positive"
            ),
            models.CheckConstraint(
                condition=Q(amount_funded__gte=0)
                & Q(amount_funded__lte=F("amount_called")),
                name="amount_funded_within_called",
            ),
        ]

    @property
    def amount_remaining(self):
        return self.amount_called - self.amount_funded

    def __str__(self):
        return f"{self.expected_reference} - {self.investor.name}"

class BankTransaction(models.Model):
    class Status(models.TextChoices):
        SUGGESTED = "suggested"
        NEEDS_REVIEW = "needs_review"
        RECONCILED = "reconciled"
        IGNORED = "ignored"

    organization = models.ForeignKey(
        Organization, on_delete=models.PROTECT, related_name="transactions"
    )
    date = models.DateField()
    description = models.TextField()
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    bank_reference = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=Status.choices)
    review_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "bank_reference"],
                name="unique_bank_reference_per_org",
            ),
            models.CheckConstraint(
                condition=~Q(amount=0), name="transaction_amount_not_zero"
            ),
        ]

    @property
    def is_credit(self):
        return self.amount > 0

    def __str__(self):
        return f"{self.bank_reference} {self.amount}"