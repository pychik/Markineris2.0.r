import hashlib
import hmac

from werkzeug.security import check_password_hash, generate_password_hash

# pbkdf2 понимает и Werkzeug 2.x: service_accounts_app проверяет пароли service_accounts_users своим
# Werkzeug, и при откате релиза новые хеши тоже остаются рабочими
PASSWORD_METHOD = "pbkdf2:sha256"
LEGACY_PREFIX = "sha256$"


def hash_password(password: str) -> str:
    return generate_password_hash(password, method=PASSWORD_METHOD)


def check_password(pw_hash: str | None, password: str | None) -> bool:
    """check_password_hash плюс старые хеши "sha256$соль$hex" (method='sha256' в Werkzeug 2.x).

    Werkzeug 3 такие хеши не принимает, а ими записано большинство паролей пользователей.
    """
    if not pw_hash or not password:
        return False
    if pw_hash.startswith(LEGACY_PREFIX):
        _, salt, digest = (pw_hash.split("$", 2) + [""])[:3]
        if salt:
            expected = hmac.new(salt.encode(), password.encode(), hashlib.sha256).hexdigest()
        else:
            expected = hashlib.sha256(password.encode()).hexdigest()
        return hmac.compare_digest(expected, digest)
    return check_password_hash(pw_hash, password)


def is_legacy_hash(pw_hash: str | None) -> bool:
    return bool(pw_hash) and pw_hash.startswith(LEGACY_PREFIX)
