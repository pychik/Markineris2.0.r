"""Composition rule shared by clothing forms, imports and order copies."""

import re


LEATHER_TNVED_PREFIX = "4203"
LEATHER_MATERIAL_PATTERN = (
    r"(?:^|[,;\n/+])\s*(?:\d+(?:[.,]\d+)?\s*%?\s*)?"
    r"(?:кожа|натуральная\s+кожа|композиционная\s+кожа)"
    r"(?:\s*\d+(?:[.,]\d+)?\s*%?)?\s*(?=$|[,;\n/+])"
)
LEATHER_TNVED_CONTENT_ERROR = (
    "ТН ВЭД с первыми цифрами 4203 разрешён только при наличии в составе "
    "материала «Кожа», «Натуральная кожа» или «Композиционная кожа»."
)
_LEATHER_MATERIAL_RE = re.compile(LEATHER_MATERIAL_PATTERN, re.IGNORECASE)

LEATHER_TNVED_CONTENT_RULE = {
    "prefix": LEATHER_TNVED_PREFIX,
    "materialPattern": LEATHER_MATERIAL_PATTERN,
    "message": LEATHER_TNVED_CONTENT_ERROR,
}


def clothes_tnved_content_error(tnved_code, content) -> str | None:
    """Return an error for 4203 without leather; other prefixes need no parsing."""
    if not str(tnved_code or "").strip().startswith(LEATHER_TNVED_PREFIX):
        return None
    if _LEATHER_MATERIAL_RE.search(str(content or "")):
        return None
    return LEATHER_TNVED_CONTENT_ERROR
