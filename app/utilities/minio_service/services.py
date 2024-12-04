from contextlib import contextmanager
from typing import IO, Optional

from flask import Response
from minio import Minio

from config import settings
from logger import logger
from utilities.minio_service.dto import DetailMinIOResponseDTO


class S3Service:
    def __init__(self, endpoint: str, access_key: str, secret_key: str) -> None:
        self.access_key = access_key
        self.secret_key = secret_key
        self.endpoint = endpoint

    @contextmanager
    def get_client(self) -> Minio:
        client = Minio(
            endpoint=self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=False,
        )
        yield client

    def get_object(self, object_name: str, bucket_name: str) -> DetailMinIOResponseDTO:
        with self.get_client() as client:
            response = client.get_object(bucket_name=bucket_name, object_name=object_name)
            return DetailMinIOResponseDTO(data=response.data, size=response.headers["Content-Length"])

    def list_objects(self, bucket_name: str, **kwargs) -> list[Optional[str]]:
        with self.get_client() as client:
            return [obj.object_name for obj in client.list_objects(bucket_name=bucket_name, **kwargs)]

    def get_object_url(self, object_name: str, bucket_name: str) -> str:
        with self.get_client() as client:
            return client.get_presigned_url(method="GET", bucket_name=bucket_name, object_name=object_name)

    def upload_file(
            self,
            file_data: IO[bytes],
            object_name: str,
            bucket_name: str,
            content_type="application/octet-stream",
    ) -> None:
        file_data.seek(0, 2)
        file_size = file_data.tell()
        file_data.seek(0)
        with self.get_client() as client:
            client.put_object(
                bucket_name=bucket_name,
                object_name=object_name,
                data=file_data,
                length=file_size,
                content_type=content_type,
            )

    def remove_object(self, object_name: str, bucket_name: str) -> None:
        with self.get_client() as client:
            client.remove_object(bucket_name=bucket_name, object_name=object_name)


def download_file_from_minio(bucket_name: str, object_name: str, download_name: str) -> Response:
    try:
        s3_service = get_s3_service()
        response = s3_service.get_object(object_name=object_name, bucket_name=bucket_name)

        return Response(
            response.data,
            headers={
                'Content-Disposition': f'attachment; filename={download_name}',
                'Content-Type': 'application/octet-stream'
            }
        )
    except Exception as e:
        logger.exception("Ошибка скачивания файла из хранилища")


def get_s3_service() -> S3Service:
    return S3Service(
        endpoint=settings.MINIO_API_URL,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
    )
