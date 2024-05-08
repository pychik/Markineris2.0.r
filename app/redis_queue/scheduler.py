import warnings

from rq import Queue
from rq_scheduler.scheduler import Scheduler

from config import settings
from redis_queue.callbacks import on_success_periodic_task, on_failure_periodic_task
from redis_queue.connection import conn
from redis_queue.tasks import daily_tasks, delete_order_files_from_server, delete_restore_link_periodic_task
from views.crm.helpers import helpers_crm_mpo_so_task

warnings.filterwarnings("ignore")


def get_queue_dynamic_cron_str():
    from models import ServerParam
    from logger import logger
    from settings.start import app
    with app.app_context():
        default_params = ServerParam.query.get(1)
        if default_params and default_params.auto_sent_minutes:
            logger.warning(f"Auto sent minutes: {settings.OrderStage.minutes_to_cron(default_params.auto_sent_minutes)}")
            return settings.OrderStage.minutes_to_cron(minutes=default_params.auto_sent_minutes)
    logger.warning(f"Auto sent minutes: {settings.OrderStage.DEFAULT_AS_CRON_STRING}")
    return settings.OrderStage.DEFAULT_AS_CRON_STRING


queue = Queue(settings.RQ_SCHEDULER_QUEUE_NAME, connection=conn)
scheduler = Scheduler(queue=queue, connection=queue.connection)

queue_dynamic = Queue(settings.RQ_DYNSCHEDULER_QUEUE_NAME, connection=conn)
scheduler_dynamic = Scheduler(queue=queue_dynamic, connection=queue_dynamic.connection)

scheduler.cron(
    "58 23 * * *",
    func=daily_tasks,
    on_success=on_success_periodic_task,
    on_failure=on_failure_periodic_task,
    queue_name=settings.RQ_SCHEDULER_QUEUE_NAME
)

scheduler.cron(
    "*/30 * * * *",
    func=delete_restore_link_periodic_task,
    on_success=on_success_periodic_task,
    on_failure=on_failure_periodic_task,
    queue_name=settings.RQ_SCHEDULER_QUEUE_NAME
)

scheduler.cron(
    "0 0 */3 * *",
    func=delete_order_files_from_server,
    on_success=on_success_periodic_task,
    on_failure=on_failure_periodic_task,
    queue_name=settings.RQ_SCHEDULER_QUEUE_NAME
)

scheduler_dynamic.cron(
    cron_string=get_queue_dynamic_cron_str(),
    func=helpers_crm_mpo_so_task,
    on_success=on_success_periodic_task,
    on_failure=on_failure_periodic_task,
    queue_name=settings.RQ_DYNSCHEDULER_QUEUE_NAME
)


if __name__ == '__main__':
    scheduler.run()
    scheduler_dynamic.run()
