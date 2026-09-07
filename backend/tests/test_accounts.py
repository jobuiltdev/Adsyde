import uuid

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction


@pytest.mark.django_db
def test_user_manager_normalizes_email_and_uses_uuid():
    user = get_user_model().objects.create_user("PERSON@Example.COM", "secure-test-password")
    assert user.email == "person@example.com"
    assert isinstance(user.pk, uuid.UUID)
    assert user.check_password("secure-test-password")
    assert not user.is_staff


@pytest.mark.django_db
def test_email_uniqueness_is_case_insensitive():
    users = get_user_model().objects
    users.create_user("person@example.com", "secure-test-password")
    with pytest.raises(IntegrityError), transaction.atomic():
        users.model.objects.bulk_create([users.model(email="PERSON@example.com")])
