from logger import logger


def on_failure_telegram(job, connection, exc_type, exc_value, traceback):
    logger.error(
        f"Job {job.id} failed with exception {exc_type}: {exc_type} - {exc_value}\n{traceback}"
    )


def on_success_telegram(job, connection, result, *args, **kwargs):
    # logger.info(f"Job {job.id} succeeded complete with result: {result}\n{args=}\n{kwargs=}")
    pass


def on_failure_gt(job, connection, exc_type, exc_value, traceback):
    logger.error(
        f"Job {job.id} failed with exception {exc_type}: {exc_type} - {exc_value}\n{traceback}"
    )


def on_success_gt(job, connection, result, *args, **kwargs):
    # logger.info(f"Job {job.id} succeeded complete with result: {result}\n{args=}\n{kwargs=}")
    pass


def on_failure_periodic_task(job, connection, exc_type, exc_value, traceback):
    logger.critical(
        f"Job {job.id} failed with exception {exc_type} for {job.func}: {exc_type} - {exc_value}\n{traceback}"
    )


def on_success_periodic_task(job, connection, result, *args, **kwargs):
    logger.info(f"Job {job.id} succeeded complete with result: {result}\n{args=}\n{kwargs=}")
