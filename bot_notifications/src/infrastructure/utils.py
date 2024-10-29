import io
import logging

import uuid
import hashlib
from uuid import uuid4

from aiogram.types import Message, File

from src.core.config import settings
from src.init_bot import bot
from src.service.s3 import get_s3_service

logger = logging.getLogger(__name__)


class FileSizeError(Exception):
    """ Размер файла не проходит по лимитам. """


class FileExtensionError(Exception):
    """ Формат файла не корректный. """


def generate_verification_code() -> str:
    return hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()[::2]


def check_file_extension(extension: str, extensions: tuple[str]) -> bool:
    return extension in extensions


def get_file_extension(file_path: str) -> str:
    return file_path.split('/')[-1].split('.')[-1]


def build_filename(user_login_name: str, extension: str) -> str:
    uuid_prefix = str(uuid4())[:8]
    return f'{uuid_prefix}_{user_login_name}.{extension}'


async def validate_photo_and_get_filename(file_info: File, user_service, tg_user_schema) -> str | None:
    logger.info(f"FILE SIZE - {file_info.file_size}")

    if file_info.file_size > settings.MAX_FILE_SIZE:
        raise FileSizeError(
            f"Размер файла больше чем {settings.MAX_FILE_SIZE // (1024*1024)} мб."
        )

    extension = get_file_extension(file_info.file_path)
    if not check_file_extension(extension=extension, extensions=settings.ALLOWED_BILL_EXTENSIONS):
        raise FileExtensionError(
            f"Формат переданного файла {extension} не корректен, доступные: {', '.join(settings.ALLOWED_BILL_EXTENSIONS)}"
        )

    tg_user = await user_service.get_user(user_id=tg_user_schema.tg_user_id)
    flask_user = await user_service.get_flask_user_by_id(user_id=tg_user.flask_user_id)

    flask_user_login_name = flask_user.login_name if flask_user else "Noname"

    filename = build_filename(flask_user_login_name, extension)

    return filename


async def download_bill_img(message: Message, user_service, tg_user_schema) -> str | None:
    if message.content_type == "photo":
        file_id = message.photo[-1].file_id
    elif message.content_type == "document":
        file_id = message.document.file_id
    else:
        return

    try:
        file_info = await bot.get_file(file_id)

        filename = await validate_photo_and_get_filename(
            file_info=file_info,
            user_service=user_service,
            tg_user_schema=tg_user_schema
        )
    except FileSizeError as e:
        logger.error(str(e))
        raise FileSizeError(str(e))

    except FileExtensionError as e:
        logger.error(str(e))
        raise FileExtensionError(str(e))

    except Exception as e:
        logger.exception("Ошибка валидации файла фото чека.")
        raise Exception(str(e))
    else:
        try:
            image_stream = io.BytesIO()
            await bot.download_file(file_path=file_info.file_path, destination=image_stream)
            image_stream.seek(0)

            s3_service = get_s3_service()
            s3_service.upload_file(
                file_data=image_stream,
                object_name=filename,
                bucket_name=settings.MINIO_BILL_BUCKET_NAME,
            )
        except Exception:
            logger.exception("Ошибка при скачивании и сохранении фото чека")
            return
        return filename


def get_qr_code(filename: str):
    return f"{settings.qr_image_dir_path}/{filename}"
