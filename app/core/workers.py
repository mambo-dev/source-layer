from celery import Celery
from app.settings import settings
from prometheus_client import multiprocess
from celery.signals import worker_process_shutdown


@worker_process_shutdown.connect
def cleanup_worker_metrics(pid=None, **kwargs):
    if pid is not None:
        multiprocess.mark_process_dead(pid)

celery = Celery(
    "anandapath",
    broker = settings.celery_broker_url,
    backend = settings.celery_result_backend,
    include=["app.pipeline.ingestion"]
)

celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    result_expires=3600,
    broker_connection_retry_on_startup=True,
    worker_send_task_events=True,
    task_send_test_event = True
)