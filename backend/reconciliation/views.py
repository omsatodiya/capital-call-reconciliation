from rest_framework.generics import ListAPIView

from .mixins import OrganizationScopedMixin
from django.db.models import Prefetch
from .models import BankTransaction, LineItem, Match
from .serializers import BankTransactionSerializer, LineItemSerializer

from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from django.core.exceptions import ObjectDoesNotExist
from rest_framework.exceptions import NotFound

from .services.actions import ActionConflict, approve_match, ignore_transaction, reject_match

from .mixins import OrganizationScopedMixin
from .models import LineItem
from .serializers import LineItemSerializer
from .services.imports import ImportFileError, import_bank_statement


class LineItemListView(OrganizationScopedMixin, ListAPIView):
    serializer_class = LineItemSerializer

    def get_queryset(self):
        return LineItem.objects.filter(
            organization=self.organization
        ).select_related("investor", "capital_call")

class BankStatementImportView(OrganizationScopedMixin, APIView):
    parser_classes = [MultiPartParser]

    def post(self, request):
        uploaded_file = request.FILES.get("file")
        if uploaded_file is None:
            return Response(
                {"detail": "Upload a CSV file in the 'file' field."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            summary = import_bank_statement(self.organization, uploaded_file)
        except ImportFileError as error:
            return Response({"detail": str(error)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(summary, status=status.HTTP_201_CREATED)

class TransactionListView(OrganizationScopedMixin, ListAPIView):
    serializer_class = BankTransactionSerializer

    def get_queryset(self):
        matches = Match.objects.select_related("line_item__investor")
        return BankTransaction.objects.filter(
            organization=self.organization
        ).prefetch_related(Prefetch("matches", queryset=matches))

def run_action(action, organization, object_id):
    try:
        bank_transaction = action(organization, object_id)
    except ObjectDoesNotExist:
        raise NotFound()
    except ActionConflict as error:
        return Response({"detail": str(error)}, status=status.HTTP_409_CONFLICT)
    return Response(BankTransactionSerializer(bank_transaction).data)


class ApproveMatchView(OrganizationScopedMixin, APIView):
    def post(self, request, pk):
        return run_action(approve_match, self.organization, pk)


class RejectMatchView(OrganizationScopedMixin, APIView):
    def post(self, request, pk):
        return run_action(reject_match, self.organization, pk)


class IgnoreTransactionView(OrganizationScopedMixin, APIView):
    def post(self, request, pk):
        return run_action(ignore_transaction, self.organization, pk)