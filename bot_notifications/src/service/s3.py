from contextlib import contextmanager
from typing import IO

from minio import Minio

from src.core.config import settings
from src.schemas.minio import DetailMinIOResponseDTO


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

    def upload_file(self, file_data: IO[bytes], object_name: str, bucket_name: str) -> None:
        file_data.seek(0, 2)
        file_size = file_data.tell()
        file_data.seek(0)
        with self.get_client() as client:
            client.put_object(
                bucket_name=bucket_name,
                object_name=object_name,
                data=file_data,
                length=file_size,
            )

    def get_object(self, object_name: str, bucket_name: str) -> DetailMinIOResponseDTO:
        with self.get_client() as client:
            response = client.get_object(bucket_name=bucket_name, object_name=object_name)
            return DetailMinIOResponseDTO(data=response.data, size=response.headers["Content-Length"])


def get_s3_service() -> S3Service:
    return S3Service(
        endpoint=settings.MINIO_API_URL,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
    )
