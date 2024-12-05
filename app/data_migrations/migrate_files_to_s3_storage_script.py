import json
import os

from config import settings
from app.logger import logger
from utilities.minio_service.services import get_s3_service


def file_migrator(dir_path: str, bucket_name: str) -> None:
    s3_service = get_s3_service()
    success_uploads = 0
    error_uploads = []

    def upload_directory(current_path: str):
        nonlocal success_uploads

        for root, dirs, files in os.walk(current_path):
            for file in files:
                if file.endswith('.py'):
                    continue

                local_file_path = os.path.join(root, file)
                relative_path = os.path.relpath(local_file_path, current_path)
                s3_key = os.path.join(relative_path)

                if s3_key.endswith(".css"):
                    content_type = "text/css"
                elif s3_key.endswith(".js"):
                    content_type = "text/javascript"
                elif s3_key.endswith(".svg"):
                    content_type = "image/svg+xml"
                else:
                    content_type = "application/octet-stream"
                try:
                    with open(local_file_path, "rb") as f:
                        s3_service.upload_file(
                            bucket_name=bucket_name,
                            object_name=s3_key,
                            file_data=f,
                            content_type=content_type,
                        )
                        success_uploads += 1
                except Exception as e:
                    logger.error(f"Не удалось переместить в бакет {bucket_name} файл {s3_key}. Ошибка - {str(e)}")
                    error_uploads.append(s3_key)

    upload_directory(dir_path)

    logger.info(f"Успешно загружено {success_uploads} файлов из {len(error_uploads) + success_uploads} в бакет {bucket_name}.")
    if error_uploads:
        logger.info(f"Файлы не загруженные в бакет {bucket_name} из-за ошибок - {json.dumps(', '.join(error_uploads))}")


if __name__ == '__main__':
    dir_path_crm = os.path.join(settings.DOWNLOAD_DIR, 'crm')
    dir_path_bill = os.path.join(settings.DOWNLOAD_DIR, 'bill_imgs')
    file_migrator(dir_path_crm, bucket_name=settings.MINIO_CRM_BUCKET_NAME)
    file_migrator(dir_path_bill, bucket_name=settings.MINIO_BILL_BUCKET_NAME)
    file_migrator(settings.DOWNLOAD_DIR_STATIC, bucket_name="static")
