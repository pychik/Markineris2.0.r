from aiogram import Bot

from core.config import settings

TOKEN = settings.BOT_API_TOKEN.get_secret_value()
bot = Bot(token=TOKEN, parse_mode="markdown")
