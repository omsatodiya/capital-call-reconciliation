from django.urls import path

from . import views

urlpatterns = [
    path("line-items/", views.LineItemListView.as_view(), name="line-item-list"),
    path("imports/", views.BankStatementImportView.as_view(), name="import"),
    path("transactions/", views.TransactionListView.as_view(), name="transaction-list"),
]