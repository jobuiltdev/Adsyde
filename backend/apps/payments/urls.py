from django.urls import path

from .views import (
    PackageListView,
    PaymentDetailView,
    PaymentInitializeView,
    PaymentListView,
    PaymentVerifyView,
    PaystackWebhookView,
)

urlpatterns = [
    path("payments/packages/", PackageListView.as_view(), name="payment-packages"),
    path("payments/", PaymentListView.as_view(), name="payment-list"),
    path("payments/initialize/", PaymentInitializeView.as_view(), name="payment-initialize"),
    path("payments/<uuid:payment_id>/", PaymentDetailView.as_view(), name="payment-detail"),
    path(
        "payments/<uuid:payment_id>/verify/",
        PaymentVerifyView.as_view(),
        name="payment-verify",
    ),
    path(
        "payments/webhooks/paystack/",
        PaystackWebhookView.as_view(),
        name="paystack-webhook",
    ),
]
