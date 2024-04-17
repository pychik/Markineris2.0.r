from loguru import logger

from config import settings

logger.add(
    f'{settings.LOG_PATH}/info.log',
    filter=lambda record: record['level'].name == 'INFO',
    format=settings.LOG_FORMAT,
    rotation='1 MB',
    compression='zip',
)
logger.add(
    f'{settings.LOG_PATH}/error.log',
    filter=lambda record: record['level'].name in ['ERROR', 'CRITICAL', 'WARNING'],
    format=settings.LOG_FORMAT,
    rotation='1 MB',
    compression='zip',
)
