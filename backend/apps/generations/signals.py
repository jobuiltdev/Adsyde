from django.db import transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import Generation


@receiver(post_delete, sender=Generation)
def delete_generation_result_after_commit(sender, instance, **kwargs):
    if instance.result_file.name:
        storage = instance.result_file.storage
        name = instance.result_file.name
        transaction.on_commit(lambda: storage.delete(name))
