from celery import Celery
from app.settings import settings

celery = Celery(
    "anandapath",
    broker = settings.celery_broker_url,
    backend = settings.celery_result_backend
)

celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    result_expires=3600,
    broker_connection_retry_on_startup=True,
)