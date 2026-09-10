from django.db import transaction
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .serializers import CreditTransactionSerializer, WalletSerializer
from .services import get_or_create_wallet


class WalletView(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "credit_wallet"

    def get(self, request):
        with transaction.atomic():
            wallet = get_or_create_wallet(request.user)
        return Response(WalletSerializer(wallet).data)


class CreditTransactionListView(generics.ListAPIView):
    serializer_class = CreditTransactionSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "credit_history"

    def get_queryset(self):
        with transaction.atomic():
            wallet = get_or_create_wallet(self.request.user)
        return wallet.transactions.all()
