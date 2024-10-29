export $(grep -v '^#' .env | xargs -0)
python3 data_migrations/migrate_files_to_s3_storage_script.py