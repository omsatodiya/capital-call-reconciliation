from rest_framework.generics import ListAPIView

from .mixins import OrganizationScopedMixin
from .models import LineItem
from .serializers import LineItemSerializer

from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

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