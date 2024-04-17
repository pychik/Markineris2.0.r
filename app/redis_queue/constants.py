from rq import Retry

from config import settings
from redis_queue.callbacks import (
    on_failure_telegram,
    on_success_telegram,
    on_failure_gt,
    on_success_gt
)
from redis_queue.connection import conn

TELEGRAM_JOB_PARAMS = {
    "queue": settings.RQ_DEFAULT_QUEUE_NAME,
    "retry": Retry(max=3),
    "connection": conn,
    "on_success": on_success_telegram,
    "on_failure": on_failure_telegram,
}

NOTIFICATION_TG_JOB_PARAMS = {
    "queue": settings.NOTIFICATION_QUEUE_NAME,
    "retry": Retry(max=3),
    "connection": conn,
    "on_success": on_success_telegram,
    "on_failure": on_failure_telegram,
}

NOTIFICATION_GT_JOB_PARAMS = {
    "queue": settings.GT_QUEUE_NAME,
    "retry": Retry(max=3),
    "connection": conn,
    "on_success": on_success_gt,
    "on_failure": on_failure_gt,
}
