from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .client import get_fsa_certificate_client, get_fsa_declaration_client
from .constants import (
    DOC_TYPE_CERTIFICATE,
    DOC_TYPE_DECLARATION,
    VERDICT_ACTIVE,
    VERDICT_ERROR,
    VERDICT_EXPIRED,
    VERDICT_NOT_FOUND,
)
from .exceptions import FsaApiError


def _parse_end_date(end_date: str | None) -> datetime | None:
    if not end_date:
        return None

    for fmt in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(end_date, fmt)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    return None


def _verdict_for(raw: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
    if not raw.get("exists"):
        return VERDICT_NOT_FOUND, None

    data = {
        "number": raw.get("number"),
        "applicant": raw.get("applicant"),
        "manufacturer": raw.get("manufacturer"),
        "product": raw.get("product"),
        "reg_date": raw.get("reg_date"),
        "end_date": raw.get("end_date"),
    }

    end_date = _parse_end_date(raw.get("end_date"))
    if end_date and end_date < datetime.now(timezone.utc):
        return VERDICT_EXPIRED, data

    return VERDICT_ACTIVE, data


def check_rd(doc_type: str, number: str) -> dict[str, Any]:
    """Checks a declaration or certificate number against the FSA registry and returns a
    result carrying an explicit verdict (found/active/expired), the same contract the future
    order-creation RD check will rely on to accept/reject a document."""

    if doc_type == DOC_TYPE_DECLARATION:
        client = get_fsa_declaration_client()
    elif doc_type == DOC_TYPE_CERTIFICATE:
        client = get_fsa_certificate_client()
    else:
        return {"ok": False, "found": False, "verdict": VERDICT_ERROR, "error": f"Неизвестный тип РД: {doc_type}", "data": None}

    try:
        raw = client.check(number)
    except FsaApiError as exc:
        return {"ok": False, "found": False, "verdict": VERDICT_ERROR, "error": str(exc), "data": None}

    verdict, data = _verdict_for(raw)

    return {
        "ok": True,
        "found": verdict != VERDICT_NOT_FOUND,
        "verdict": verdict,
        "error": None,
        "data": data,
    }
