import logging

from aiogram import Bot
from aiogram.client.session.aiohttp import AiohttpSession

from src.core.config import settings

TOKEN = settings.BOT_API_TOKEN.get_secret_value()
proxy = settings.TELEGRAM_PROXY.strip() if settings.TELEGRAM_PROXY else None

session_kwargs = {
    "timeout": settings.TELEGRAM_REQUEST_TIMEOUT_SEC,
}
if proxy:
    session_kwargs["proxy"] = proxy

try:
    session = AiohttpSession(**session_kwargs)
except RuntimeError as exc:
    if proxy and "aiohttp-socks" in str(exc):
        logging.getLogger(__name__).warning(
            "aiohttp-socks не установлен, запуск без TELEGRAM_PROXY"
        )
        session = AiohttpSession(timeout=settings.TELEGRAM_REQUEST_TIMEOUT_SEC)
    else:
        raise

bot = Bot(token=TOKEN, session=session, parse_mode="markdown")
