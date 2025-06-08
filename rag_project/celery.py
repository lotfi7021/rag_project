import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rag_project.settings")

app = Celery("rag_project")

app.config_from_object("django.conf:settings", namespace="CELERY")

# تهم برشة هذي: يلقط جميع المهام في كل التطبيقات
app.autodiscover_tasks()
