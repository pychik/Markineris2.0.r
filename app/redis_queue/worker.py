from rq import Worker

from config import settings
from redis_queue.connection import conn
from settings.start import app

worker = Worker(
    queues=[
        settings.RQ_DEFAULT_QUEUE_NAME,
        settings.RQ_SCHEDULER_QUEUE_NAME,
        settings.RQ_DYNSCHEDULER_QUEUE_NAME,
        settings.NOTIFICATION_QUEUE_NAME,
        settings.GT_QUEUE_NAME,
    ],
    connection=conn,
)

if __name__ == '__main__':
    with app.app_context():
        worker.work()
