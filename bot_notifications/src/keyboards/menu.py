from aiogram import Bot
from aiogram.types import BotCommand


async def add_menu_commands(bot: Bot) -> None:
    await bot.set_my_commands(
        [
            BotCommand(command='/help', description='Помощь'),
            BotCommand(command="/cancel", description='Отмена действия'),
        ]
    )
