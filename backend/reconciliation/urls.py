from django.urls import path

from . import views

urlpatterns = [
    path("line-items/", views.LineItemListView.as_view(), name="line-item-list"),
    path("imports/", views.BankStatementImportView.as_view(), name="import"),
    path("transactions/", views.TransactionListView.as_view(), name="transaction-list"),
    path(
        "transactions/<int:pk>/ignore/",
        views.IgnoreTransactionView.as_view(),
        name="transaction-ignore",
    ),
    path("matches/<int:pk>/approve/", views.ApproveMatchView.as_view(), name="match-approve"),
    path("matches/<int:pk>/reject/", views.RejectMatchView.as_view(), name="match-reject"),
    path("organizations/", views.OrganizationListView.as_view(), name="organization-list"),
]