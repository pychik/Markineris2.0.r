from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .client import get_fsa_certificate_client, get_fsa_declaration_client
from .constants import (
    DOC_TYPE_CERTIFICATE,
    DOC_TYPE_DECLARATION,
    VERDICT_ACTIVE,
    VERDICT_COUNTRY_MISMATCH,
    VERDICT_ERROR,
    VERDICT_EXPIRED,
    VERDICT_NOT_FOUND,
    VERDICT_TNVED_MISMATCH,
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
        "tnved_codes": raw.get("tnved_codes") or [],
        "country": raw.get("country"),
    }

    end_date = _parse_end_date(raw.get("end_date"))
    if end_date and end_date < datetime.now(timezone.utc):
        return VERDICT_EXPIRED, data

    return VERDICT_ACTIVE, data


def check_rd(
    doc_type: str,
    number: str,
    tnved_code: str | None = None,
    country: str | None = None,
) -> dict[str, Any]:
    """Checks a declaration or certificate number against the FSA registry and returns a
    result carrying an explicit verdict (found/active/expired/tnved_mismatch/country_mismatch),
    the same contract the future order-creation RD check will rely on to accept/reject a document.

    When `tnved_code`/`country` are given, they're compared against what FSA has on file for
    this RD (resolved via the /nsi/api/multi reference lookup) - a document can be found and
    still not valid for the position it's attached to if either doesn't match. Comparison is
    skipped (not treated as a mismatch) when FSA didn't return data for that field - we can't
    judge a mismatch we have no data for. TNVED is checked first; country is only checked if
    TNVED already matched (a single verdict can only carry one problem at a time).
    """

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

    if verdict == VERDICT_ACTIVE and tnved_code and data is not None:
        rd_tnveds = data.get("tnved_codes") or []
        if rd_tnveds and tnved_code not in rd_tnveds:
            verdict = VERDICT_TNVED_MISMATCH

    if verdict == VERDICT_ACTIVE and country and data is not None:
        rd_country = data.get("country")
        if rd_country and rd_country.strip().upper() != country.strip().upper():
            verdict = VERDICT_COUNTRY_MISMATCH

    return {
        "ok": True,
        "found": verdict != VERDICT_NOT_FOUND,
        "verdict": verdict,
        "error": None,
        "data": data,
    }
