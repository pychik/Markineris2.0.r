import json
import os

from config import settings
from app.logger import logger
from utilities.minio_service.services import get_s3_service


def file_migrator(dir_path: str, bucket_name: str) -> None:
    s3_service = get_s3_service()

    files = os.listdir(dir_path)

    files_count = len(files)
    success_uploads = 0
    error_uploads = []

    for file in files:
        if file.endswith('.py'):
            files_count -= 1
            continue
        try:
            with open(f"{dir_path}/{file}", "rb") as f:
                s3_service.upload_file(
                    bucket_name=bucket_name,
                    object_name=file,
                    file_data=f,
                )
                success_uploads += 1
        except Exception as e:
            logger.error(f"Не удалось переместить в бакет {bucket_name} файл {file}. Ошибка - {str(e)}")
            error_uploads.append(file)
            continue

    logger.info(f"Успешно загружено {success_uploads} файлов из {files_count} в бакет {bucket_name}.")
    if error_uploads:
        logger.info(f"Файлы не загруженные в бакет {bucket_name} из-за ошибок - {json.dumps(', '.join(error_uploads))}")


if __name__ == '__main__':
    dir_path_crm = os.path.join(settings.DOWNLOAD_DIR, 'crm')
    dir_path_bill = os.path.join(settings.DOWNLOAD_DIR, 'bill_imgs')
    file_migrator(dir_path_crm, bucket_name=settings.MINIO_CRM_BUCKET_NAME)
    file_migrator(dir_path_bill, bucket_name=settings.MINIO_BILL_BUCKET_NAME)
