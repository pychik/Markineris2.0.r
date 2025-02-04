import hashlib
import json
import mimetypes
import os

from logger import logger
from utilities.minio_service.services import get_s3_service


class S3StorageSynchronizer:

    def __init__(self):
        self._success_uploads = []
        self._error_uploads = []
        self._s3_service = get_s3_service()
        self._bucket_name = None

    def synchronize(self, dir_path: str, bucket_name: str, excluded_dirs: list[str] | None = None) -> None:
        self._bucket_name = bucket_name
        self.__upload_directory(dir_path, excluded_dirs=excluded_dirs if excluded_dirs else [])

        logger.info(f"Успешно загружено {len(self._success_uploads)} файлов "
                    f"из {len(self._error_uploads) + len(self._success_uploads)} в бакет {bucket_name}.")
        logger.info(f"Обновленные/загруженные файлы:\n{chr(10).join(self._success_uploads)}")
        if self._error_uploads:
            logger.info(f"Файлы не загруженные в бакет {bucket_name} "
                        f"из-за ошибок - {json.dumps(', '.join(self._error_uploads))}")

    def __upload_directory(self, current_path: str, excluded_dirs: list[str]) -> None:
        for root, dirs, files in os.walk(current_path):
            dirs[:] = [d for d in dirs if d not in excluded_dirs]

            for file in files:
                upload_flag = False
                if file.endswith('.py'):
                    continue

                local_file_path = os.path.join(root, file)
                relative_path = os.path.relpath(local_file_path, current_path)
                s3_key = os.path.join(relative_path)

                try:

                    s3_obj = self._s3_service.get_object(bucket_name=self._bucket_name, object_name=s3_key)
                    if not s3_obj:
                        upload_flag = True

                    if (upload_flag or self._get_file_hash(file_data=self._get_file_data(local_file_path)) !=
                            self._get_file_hash(s3_obj.data)):
                        with open(local_file_path, "rb") as f:
                            self._s3_service.upload_file(
                                bucket_name=self._bucket_name,
                                object_name=s3_key,
                                file_data=f,
                                content_type=self._get_content_type(s3_key),
                            )
                            self._success_uploads.append(s3_key)
                except Exception as e:
                    logger.error(f"Не удалось переместить в бакет {self._bucket_name} файл {s3_key}. Ошибка - {str(e)}")
                    self._error_uploads.append(s3_key)

    @staticmethod
    def _get_file_data(path):
        with open(path, 'rb') as f:
            return f.read()

    @staticmethod
    def _get_file_hash(file_data, hash_algo='md5'):
        hash_func = hashlib.new(hash_algo)
        hash_func.update(file_data)
        return hash_func.hexdigest()

    @staticmethod
    def _get_content_type(file_path) -> str:
        content_type, _ = mimetypes.guess_type(file_path)
        return content_type or "application/octet-stream"


def get_s3_storage_synchronizer() -> S3StorageSynchronizer:
    return S3StorageSynchronizer()
