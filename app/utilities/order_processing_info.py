"""Legacy CRM shipment text parsing for ordinary orders."""

from html import unescape
import re


_SINGLE_UPD = re.compile(r"^\s*([^<>]+?)\s*<br\s*/?>\s*УПД:\s*([^<>]+?)\s*$", re.IGNORECASE)


def parse_single_processing_info(value: str | None) -> tuple[str, str] | None:
    """Parse one company and UPD; refuse ambiguous or malformed legacy text."""
    match = _SINGLE_UPD.fullmatch(value or "")
    if not match:
        return None
    company, upd = (unescape(part).strip() for part in match.groups())
    return (company, upd) if company and upd else None


def split_processing_company_label(value: str | None) -> tuple[str, str]:
    """Split the saved 'company title (INN)' label, preserving historical names."""
    label = (value or "").strip()
    match = re.fullmatch(r"(.+)\s+\(([0-9]{10}|[0-9]{12})\)", label)
    return (match[1].strip(), match[2]) if match else (label, "")
