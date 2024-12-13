from config import settings
from data_migrations.migrate_files_to_s3_storage_script import get_s3_storage_synchronizer

if __name__ == '__main__':
    s3_storage_synchronizer = get_s3_storage_synchronizer()
    s3_storage_synchronizer.synchronize(
        bucket_name="static",
        dir_path=settings.DOWNLOAD_DIR_STATIC,
        excluded_dirs=["qr_imgs"],
    )
