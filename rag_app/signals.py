# rag_app/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction

from .models import Document
from .tasks import generate_embeddings_task

@receiver(post_save, sender=Document)
def generate_embeddings_on_create(sender, instance, created, **kwargs):
    if created:
        transaction.on_commit(lambda: generate_embeddings_task.delay(instance.id))
