from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken


def revoke_refresh_tokens(user) -> None:
    outstanding = OutstandingToken.objects.filter(user=user)
    existing = set(
        BlacklistedToken.objects.filter(token__in=outstanding).values_list("token_id", flat=True)
    )
    BlacklistedToken.objects.bulk_create(
        [BlacklistedToken(token=token) for token in outstanding if token.pk not in existing],
        ignore_conflicts=True,
    )
