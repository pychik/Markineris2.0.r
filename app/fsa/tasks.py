from rq.decorators import job

from config import settings
from logger import logger
from redis_queue.connection import conn

from .job_store import RdCheckJobStore
from .service import check_rd


@job(queue=settings.RD_CHECK_QUEUE_NAME, connection=conn, timeout=60, result_ttl=settings.FSA_JOB_RESULT_TTL)
def check_rd_task(request_id: str, doc_type: str, number: str) -> None:
    job_store = RdCheckJobStore()
    job_store.mark_processing(request_id)

    try:
        result = check_rd(doc_type=doc_type, number=number)
    except Exception as exc:
        logger.exception("Неожиданная ошибка при проверке РД {} ({})", number, doc_type)
        job_store.mark_error(request_id, str(exc))
        return

    job_store.mark_done(request_id, result)
