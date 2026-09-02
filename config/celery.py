import os

from celery import Celery

# Celery ishga tushganda Django sozlamalarini topishi uchun
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("config")

# Sozlamalar settings.py dagi CELERY_ prefiksli o'zgaruvchilardan olinadi
app.config_from_object("django.conf:settings", namespace="CELERY")

# Har bir app ichidagi tasks.py avtomatik topiladi
app.autodiscover_tasks()
