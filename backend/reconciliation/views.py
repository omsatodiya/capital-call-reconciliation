from rest_framework.generics import ListAPIView

from .mixins import OrganizationScopedMixin
from .models import LineItem
from .serializers import LineItemSerializer


class LineItemListView(OrganizationScopedMixin, ListAPIView):
    serializer_class = LineItemSerializer

    def get_queryset(self):
        return LineItem.objects.filter(
            organization=self.organization
        ).select_related("investor", "capital_call")