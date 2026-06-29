import secrets

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from external_processors.config import EXTERNAL_PROCESSOR_CONFIG
from models import ExternalProcessor, db


def normalize_allowed_ips(value: list[str] | str | None) -> str:
    if value is None:
        return ''
    if isinstance(value, str):
        raw_items = value.split(',')
    else:
        raw_items = value

    normalized = []
    for item in raw_items:
        ip = (item or '').strip()
        if ip and ip not in normalized:
            normalized.append(ip)
    return ','.join(normalized)


def allowed_ips_as_list(value: str | None) -> list[str]:
    if not value:
        return []
    return [ip.strip() for ip in value.split(',') if ip.strip()]


def generate_key_id() -> str:
    return secrets.token_hex(8)


def generate_shared_secret() -> str:
    return secrets.token_hex(32)


def _source_label_exists(source_label: str, exclude_processor_id: int | None = None) -> bool:
    query = db.session.query(ExternalProcessor.id).filter(ExternalProcessor.source_label == source_label)
    if exclude_processor_id is not None:
        query = query.filter(ExternalProcessor.id != exclude_processor_id)
    return db.session.query(query.exists()).scalar()


def build_unique_source_label(source_label: str, exclude_processor_id: int | None = None) -> str:
    candidate = source_label
    suffix = 2
    while _source_label_exists(candidate, exclude_processor_id=exclude_processor_id):
        candidate = f'{source_label}-{suffix}'
        suffix += 1
    return candidate


def serialize_external_processor(processor: ExternalProcessor, include_secret: bool = False) -> dict:
    payload = {
        'id': processor.id,
        'name': processor.name,
        'key_id': processor.key_id,
        'allowed_ips': allowed_ips_as_list(processor.allowed_ips),
        'minio_bucket_name': processor.minio_bucket_name,
        'minio_prefix': processor.minio_prefix,
        'ttl_seconds': processor.ttl_seconds,
        'nonce_ttl_seconds': processor.nonce_ttl_seconds,
        'batch_size': processor.batch_size,
        'confirmation_timeout_seconds': processor.confirmation_timeout_seconds,
        'source_label': processor.source_label,
        'is_active': processor.is_active,
        'created_at': processor.created_at.isoformat() if processor.created_at else None,
        'updated_at': processor.updated_at.isoformat() if processor.updated_at else None,
    }
    if include_secret:
        payload['shared_secret'] = processor.shared_secret
    return payload


def list_external_processors() -> list[ExternalProcessor]:
    return (
        db.session.query(ExternalProcessor)
        .order_by(ExternalProcessor.created_at.desc(), ExternalProcessor.id.desc())
        .all()
    )


def get_external_processor(external_processor_id: int) -> ExternalProcessor | None:
    return db.session.get(ExternalProcessor, external_processor_id)


def get_active_external_processor_by_key_id(key_id: str) -> ExternalProcessor | None:
    return (
        db.session.query(ExternalProcessor)
        .filter(ExternalProcessor.key_id == key_id)
        .filter(ExternalProcessor.is_active.is_(True))
        .first()
    )


def has_active_external_processors() -> bool:
    query = db.session.query(ExternalProcessor.id).filter(ExternalProcessor.is_active.is_(True))
    return db.session.query(query.exists()).scalar()


def create_external_processor(data: dict) -> ExternalProcessor:
    name = data['name']
    key_id = data.get('key_id') or generate_key_id()
    shared_secret = data.get('shared_secret') or generate_shared_secret()

    duplicate = (
        db.session.query(ExternalProcessor.id)
        .filter(
            or_(
                ExternalProcessor.name == name,
                ExternalProcessor.key_id == key_id,
            )
        )
        .first()
    )
    if duplicate:
        raise ValueError('External processor with the same name or key_id already exists')

    processor = ExternalProcessor(
        name=name,
        key_id=key_id,
        shared_secret=shared_secret,
        allowed_ips=normalize_allowed_ips(data['allowed_ips']),
        minio_bucket_name=data['minio_bucket_name'],
        minio_prefix=data['minio_prefix'].strip('/'),
        ttl_seconds=data.get('ttl_seconds') or EXTERNAL_PROCESSOR_CONFIG.ttl_seconds,
        nonce_ttl_seconds=data.get('nonce_ttl_seconds') or EXTERNAL_PROCESSOR_CONFIG.nonce_ttl_seconds,
        batch_size=data.get('batch_size') or EXTERNAL_PROCESSOR_CONFIG.batch_size,
        confirmation_timeout_seconds=(
            data.get('confirmation_timeout_seconds') or EXTERNAL_PROCESSOR_CONFIG.confirmation_timeout_seconds
        ),
        source_label=build_unique_source_label(data['source_label']),
        is_active=data.get('is_active', True),
    )
    db.session.add(processor)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ValueError('External processor with the same name, key_id or source_label already exists')
    return processor


def update_external_processor(processor: ExternalProcessor, data: dict) -> ExternalProcessor:
    next_name = data.get('name', processor.name)
    next_key_id = data.get('key_id', processor.key_id)
    requested_source_label = data.get('source_label')

    duplicate = (
        db.session.query(ExternalProcessor.id)
        .filter(ExternalProcessor.id != processor.id)
        .filter(
            or_(
                ExternalProcessor.name == next_name,
                ExternalProcessor.key_id == next_key_id,
            )
        )
        .first()
    )
    if duplicate:
        raise ValueError('External processor with the same name or key_id already exists')

    processor.name = next_name
    processor.key_id = next_key_id
    if 'shared_secret' in data and data['shared_secret']:
        processor.shared_secret = data['shared_secret']
    if 'allowed_ips' in data:
        processor.allowed_ips = normalize_allowed_ips(data.get('allowed_ips'))
    if 'minio_bucket_name' in data and data['minio_bucket_name'] is not None:
        processor.minio_bucket_name = data['minio_bucket_name']
    if 'minio_prefix' in data and data['minio_prefix'] is not None:
        processor.minio_prefix = data['minio_prefix'].strip('/')
    if 'ttl_seconds' in data and data['ttl_seconds'] is not None:
        processor.ttl_seconds = data['ttl_seconds']
    if 'nonce_ttl_seconds' in data and data['nonce_ttl_seconds'] is not None:
        processor.nonce_ttl_seconds = data['nonce_ttl_seconds']
    if 'batch_size' in data and data['batch_size'] is not None:
        processor.batch_size = data['batch_size']
    if 'confirmation_timeout_seconds' in data and data['confirmation_timeout_seconds'] is not None:
        processor.confirmation_timeout_seconds = data['confirmation_timeout_seconds']
    if requested_source_label is not None:
        processor.source_label = build_unique_source_label(
            requested_source_label,
            exclude_processor_id=processor.id,
        )
    if 'is_active' in data and data['is_active'] is not None:
        processor.is_active = data['is_active']

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ValueError('External processor with the same name, key_id or source_label already exists')
    return processor


def delete_external_processor(processor: ExternalProcessor) -> None:
    db.session.delete(processor)
    db.session.commit()