from __future__ import annotations

import argparse
import hashlib
import io
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import settings
from logger import logger
from tezaurus.redis_repository import RedisTezaurusRepository
from utilities.minio_service.services import get_s3_service


SNAPSHOT_FILES = (
    "versions.json",
    "colors.json",
    "countries.json",
    "clothes_tnved.json",
    "processing_companies.json",
)
MANIFEST_FILE = "manifest.json"


def _json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _object_name(filename: str, *, prefix: str | None = None) -> str:
    prefix = (prefix if prefix is not None else settings.TEZAURUS_FALLBACK_S3_PREFIX).strip("/")
    return f"{prefix}/{filename}" if prefix else filename


def _snapshot_prefix(versions: dict[str, Any]) -> str:
    base_prefix = settings.TEZAURUS_FALLBACK_S3_PREFIX.strip("/")
    root = base_prefix.rsplit("/", 1)[0] if "/" in base_prefix else "tezaurus_fallback"
    parts = []
    for key in ("colors", "countries", "tnved", "processing_companies"):
        revision = (versions.get(key) or {}).get("revision")
        parts.append(f"{key}-{revision or 0}")
    snapshot_id = "_".join(parts)
    return f"{root}/snapshots/{snapshot_id}"


def _upload_bytes(*, object_name: str, data: bytes) -> None:
    get_s3_service().upload_file(
        bucket_name=settings.TEZAURUS_FALLBACK_S3_BUCKET_NAME,
        object_name=object_name,
        file_data=io.BytesIO(data),
        content_type="application/json",
    )


def _snapshot_payloads_from_redis() -> dict[str, Any]:
    repository = RedisTezaurusRepository()

    versions = repository.get_versions()
    colors = repository.get_colors_snapshot()
    countries = repository.get_countries_snapshot()
    tnved_snapshot = repository.get_tnved_snapshot()
    clothes_tnved = tnved_snapshot.get("clothes") if isinstance(tnved_snapshot, dict) else None
    processing_companies = repository.get_processing_companies()

    payloads = {
        "versions.json": versions,
        "colors.json": colors,
        "countries.json": countries,
        "clothes_tnved.json": clothes_tnved,
        "processing_companies.json": processing_companies,
    }
    _validate_snapshot_payloads(payloads)
    return payloads


def _validate_snapshot_payloads(payloads: dict[str, Any]) -> None:
    versions = payloads.get("versions.json")
    if not isinstance(versions, dict) or not versions:
        raise ValueError("Tezaurus fallback snapshot has empty versions")

    for filename in ("colors.json", "countries.json", "clothes_tnved.json"):
        payload = payloads.get(filename)
        if not isinstance(payload, dict) or "items" not in payload:
            raise ValueError(f"Tezaurus fallback snapshot has invalid {filename}")

    companies = payloads.get("processing_companies.json")
    if not isinstance(companies, list) or not companies:
        raise ValueError("Tezaurus fallback snapshot has empty processing_companies.json")

    subcategories = ((payloads["clothes_tnved.json"].get("items") or {}).get("subcategories") or {})
    if not isinstance(subcategories, dict) or not subcategories:
        raise ValueError("Tezaurus fallback snapshot has empty clothes TNVED subcategories")


def export_tezaurus_fallback_snapshot_to_s3() -> dict[str, Any]:
    payloads = _snapshot_payloads_from_redis()
    encoded_payloads = {filename: _json_bytes(payload) for filename, payload in payloads.items()}
    created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    snapshot_prefix = _snapshot_prefix(payloads["versions.json"])

    files = {
        filename: {
            "object_name": _object_name(filename, prefix=snapshot_prefix),
            "sha256": _sha256(data),
            "size": len(data),
        }
        for filename, data in encoded_payloads.items()
    }
    manifest = {
        "schema": 1,
        "created_at": created_at,
        "versions": payloads["versions.json"],
        "files": files,
    }

    for filename, data in encoded_payloads.items():
        _upload_bytes(object_name=files[filename]["object_name"], data=data)

    manifest_data = _json_bytes(manifest)
    _upload_bytes(object_name=_object_name(MANIFEST_FILE), data=manifest_data)

    logger.info(
        "Tezaurus fallback snapshot exported to s3 bucket={} prefix={}",
        settings.TEZAURUS_FALLBACK_S3_BUCKET_NAME,
        settings.TEZAURUS_FALLBACK_S3_PREFIX,
    )
    return {
        "ok": True,
        "bucket": settings.TEZAURUS_FALLBACK_S3_BUCKET_NAME,
        "prefix": settings.TEZAURUS_FALLBACK_S3_PREFIX,
        "snapshot_prefix": snapshot_prefix,
        "files": sorted(encoded_payloads),
        "manifest": MANIFEST_FILE,
        "versions": payloads["versions.json"],
    }


def _download_manifest() -> dict[str, Any] | None:
    response = get_s3_service().get_object(
        bucket_name=settings.TEZAURUS_FALLBACK_S3_BUCKET_NAME,
        object_name=_object_name(MANIFEST_FILE),
    )
    if not response:
        return None
    manifest = json.loads(response.data.decode("utf-8"))
    return manifest if isinstance(manifest, dict) else None


def restore_tezaurus_fallback_snapshot_from_s3() -> dict[str, Any]:
    manifest = _download_manifest()
    if not manifest:
        logger.warning("Tezaurus fallback snapshot manifest is missing in s3")
        return {"ok": False, "reason": "missing_manifest"}

    files = manifest.get("files")
    if not isinstance(files, dict):
        return {"ok": False, "reason": "invalid_manifest"}

    downloaded: dict[str, bytes] = {}
    for filename in SNAPSHOT_FILES:
        file_meta = files.get(filename)
        if not isinstance(file_meta, dict):
            return {"ok": False, "reason": f"missing_manifest_file:{filename}"}

        object_name = str(file_meta.get("object_name") or _object_name(filename))
        response = get_s3_service().get_object(
            bucket_name=settings.TEZAURUS_FALLBACK_S3_BUCKET_NAME,
            object_name=object_name,
        )
        if not response:
            return {"ok": False, "reason": f"missing_s3_file:{filename}"}

        expected_hash = str(file_meta.get("sha256") or "")
        actual_hash = _sha256(response.data)
        if expected_hash and expected_hash != actual_hash:
            return {"ok": False, "reason": f"checksum_mismatch:{filename}"}

        downloaded[filename] = response.data

    payloads = {filename: json.loads(data.decode("utf-8")) for filename, data in downloaded.items()}
    _validate_snapshot_payloads(payloads)

    target_dir = Path(settings.TEZAURUS_FALLBACK_RUNTIME_DATA_DIR)
    target_dir.mkdir(parents=True, exist_ok=True)

    for filename, data in downloaded.items():
        target = target_dir / filename
        temp = target.with_suffix(f"{target.suffix}.tmp")
        temp.write_bytes(data)
        temp.replace(target)

    logger.info(
        "Tezaurus fallback snapshot restored from s3 bucket={} prefix={} to {}",
        settings.TEZAURUS_FALLBACK_S3_BUCKET_NAME,
        settings.TEZAURUS_FALLBACK_S3_PREFIX,
        target_dir,
    )
    return {
        "ok": True,
        "target_dir": target_dir.as_posix(),
        "files": sorted(downloaded),
        "versions": payloads["versions.json"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("export", "restore"))
    args = parser.parse_args()

    try:
        if args.command == "export":
            result = export_tezaurus_fallback_snapshot_to_s3()
        else:
            result = restore_tezaurus_fallback_snapshot_from_s3()
    except Exception:
        logger.exception("Tezaurus fallback snapshot command failed")
        result = {"ok": False, "reason": "unexpected_error"}
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
