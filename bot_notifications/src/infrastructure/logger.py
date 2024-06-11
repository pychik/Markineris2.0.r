from loguru import logger

from src.core.config import settings

logger.add(
    f'{settings.log_path}/info.log',
    filter=lambda record: record['level'].name == 'INFO',
    format=settings.LOG_FORMAT,
    rotation='1 MB',
    compression='zip',
)

logger.add(
    f'{settings.log_path}/error.log',
    filter=lambda record: record['level'].name in ['ERROR', 'CRITICAL', 'WARNING'],
    format=settings.LOG_FORMAT,
    rotation='1 MB',
    compression='zip',
)
