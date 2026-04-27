import re
from pathlib import PurePath
from typing import Optional
from uuid import uuid4

from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from config import settings
from utilities.exceptions import EmptyFileToUploadError
from utilities.minio_service.services import get_s3_service
from utilities.support import check_file_extension


CHAT_UPLOAD_FIELDS = ('files', 'files[]')
MAX_CHAT_FILE_NAME_LENGTH = 180
DELETED_CHAT_ATTACHMENT_CONTENT_TYPE = 'application/x-chat-attachment-deleted'
DELETED_CHAT_ATTACHMENT_PLACEHOLDER_NAME = 'Файл удален по сроку давности'
DELETED_CHAT_ATTACHMENT_STORAGE_PREFIX = '__deleted__/chat_attachments'


def is_deleted_chat_attachment(content_type: str) -> bool:
    return (content_type or '').strip() == DELETED_CHAT_ATTACHMENT_CONTENT_TYPE


def get_deleted_chat_attachment_name(original_name: str) -> str:
    return DELETED_CHAT_ATTACHMENT_PLACEHOLDER_NAME


def build_deleted_chat_attachment_storage_name(attachment_id: int) -> str:
    return f"{DELETED_CHAT_ATTACHMENT_STORAGE_PREFIX}/{attachment_id}"


def collect_chat_files(request) -> list[FileStorage]:
    files = []
    seen = set()

    for field_name in CHAT_UPLOAD_FIELDS:
        for uploaded_file in request.files.getlist(field_name):
            if not uploaded_file or not getattr(uploaded_file, 'filename', ''):
                continue

            file_key = id(uploaded_file)
            if file_key in seen:
                continue

            seen.add(file_key)
            files.append(uploaded_file)

    return files


def normalize_chat_file_name(filename: str) -> str:
    raw_name = PurePath(filename or '').name.strip()
    raw_name = raw_name.replace('/', '_').replace('\\', '_')
    raw_name = re.sub(r'[\x00-\x1f\x7f]+', ' ', raw_name)
    safe_name = re.sub(r'\s+', ' ', raw_name).strip(' .')
    if not safe_name:
        return ''

    if len(safe_name) <= MAX_CHAT_FILE_NAME_LENGTH:
        return safe_name

    if '.' not in safe_name:
        return safe_name[:MAX_CHAT_FILE_NAME_LENGTH]

    stem, ext = safe_name.rsplit('.', 1)
    max_stem_length = MAX_CHAT_FILE_NAME_LENGTH - len(ext) - 1
    return f"{stem[:max_stem_length]}.{ext}"


def build_chat_storage_name(object_prefix: str, original_name: str) -> str:
    extension = ''
    if '.' in original_name:
        safe_extension = secure_filename(original_name.rsplit('.', 1)[1].lower())
        if safe_extension:
            extension = f'.{safe_extension}'

    return f"{object_prefix}/{uuid4().hex}{extension}"


def get_uploaded_file_size(uploaded_file: FileStorage) -> int:
    uploaded_file.stream.seek(0, 2)
    size_bytes = uploaded_file.stream.tell()
    uploaded_file.stream.seek(0)
    return int(size_bytes or 0)


def validate_chat_files(files: list[FileStorage]) -> tuple[list[dict], Optional[str]]:
    prepared_files = []

    for uploaded_file in files:
        original_name = normalize_chat_file_name(uploaded_file.filename or '')
        if not original_name:
            return [], 'Не удалось определить имя файла'

        if not check_file_extension(original_name, settings.CHAT_ALLOWED_EXTENSIONS):
            allowed = ', '.join(f'.{ext}' for ext in settings.CHAT_ALLOWED_EXTENSIONS)
            return [], f'Файл {original_name} имеет неподдерживаемое расширение. Доступны: {allowed}'

        size_bytes = get_uploaded_file_size(uploaded_file)
        if size_bytes <= 0:
            return [], f'Файл {original_name} пуст'

        prepared_files.append({
            'file': uploaded_file,
            'original_name': original_name,
            'size_bytes': size_bytes,
            'content_type': ((uploaded_file.mimetype or '').strip() or 'application/octet-stream'),
        })

    return prepared_files, None


def upload_chat_files(prepared_files: list[dict], object_prefix: str) -> tuple[list[dict], Optional[str]]:
    if not prepared_files:
        return [], None

    s3_service = get_s3_service()
    uploaded_files = []

    try:
        for prepared in prepared_files:
            storage_name = build_chat_storage_name(object_prefix, prepared['original_name'])
            try:
                s3_service.upload_file(
                    file_data=prepared['file'].stream,
                    object_name=storage_name,
                    bucket_name=settings.MINIO_CRM_BUCKET_NAME,
                    content_type=prepared['content_type'],
                )
            except EmptyFileToUploadError:
                cleanup_chat_files([item['storage_name'] for item in uploaded_files])
                return [], f"Файл {prepared['original_name']} пуст"

            uploaded_files.append({
                'original_name': prepared['original_name'],
                'storage_name': storage_name,
                'content_type': prepared['content_type'],
                'size_bytes': prepared['size_bytes'],
            })
    except Exception:
        cleanup_chat_files([item['storage_name'] for item in uploaded_files])
        raise

    return uploaded_files, None


def cleanup_chat_files(storage_names: list[str]) -> None:
    if not storage_names:
        return

    s3_service = get_s3_service()
    for storage_name in storage_names:
        try:
            s3_service.remove_object(
                object_name=storage_name,
                bucket_name=settings.MINIO_CRM_BUCKET_NAME,
            )
        except Exception:
            continue