from django.urls import path

from .views import CreditTransactionListView, WalletView

urlpatterns = [
    path("credits/wallet/", WalletView.as_view(), name="credit-wallet"),
    path(
        "credits/transactions/",
        CreditTransactionListView.as_view(),
        name="credit-transactions",
    ),
]
