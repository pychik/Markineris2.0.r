import hashlib

from werkzeug.security import generate_password_hash


def make_login_name(code: str) -> str:
    return f"Agent_{code}"


def make_email(login_name: str) -> str:
    return f"{login_name}@markineris.ru"


def get_hashed_password(password: str) -> str:
    return generate_password_hash(password)


def make_password(email: str, salt: str) -> str:
    email = hashlib.sha256(email.encode()).hexdigest()
    hashed_data = hashlib.sha256(f"{email}{salt}".encode()).hexdigest()
    return hashed_data[:10]
