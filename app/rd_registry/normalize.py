import re

# Кириллические буквы, неотличимые на глаз от латинских. В номерах РД они перемешаны
# ("ЕАЭС N RU Д-CN.РА02.В.23280/26"), а оператор может набрать их в любой раскладке.
_HOMOGLYPHS = str.maketrans("АВЕКМНОРСТУХ", "ABEKMHOPCTYX")
_NOT_KEY_CHARS = re.compile(r"[^0-9A-ZА-ЯЁ]")


def rd_key(value: str | None) -> str:
    """Ключ поиска номера РД: верхний регистр, двойники -> латиница, без пробелов и пунктуации.

    Тот же алгоритм продублирован в static/rd_registry/rd_picker.js (rdKey) - менять синхронно.
    """
    return _NOT_KEY_CHARS.sub("", (value or "").upper().translate(_HOMOGLYPHS))
