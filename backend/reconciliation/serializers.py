from rest_framework import serializers

from .models import LineItem


class LineItemSerializer(serializers.ModelSerializer):
    investor_name = serializers.CharField(source="investor.name", read_only=True)
    capital_call_number = serializers.IntegerField(
        source="capital_call.number", read_only=True
    )
    amount_remaining = serializers.DecimalField(
        max_digits=14, decimal_places=2, read_only=True
    )

    class Meta:
        model = LineItem
        fields = [
            "id",
            "expected_reference",
            "investor_name",
            "capital_call_number",
            "amount_called",
            "amount_funded",
            "amount_remaining",
            "status",
        ]