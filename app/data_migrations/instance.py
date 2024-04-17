from data_migrations.etl_service import ETLUploadProcessUserAndPartnerCode
from settings.start import db


etl_service = ETLUploadProcessUserAndPartnerCode(session=db.session)
