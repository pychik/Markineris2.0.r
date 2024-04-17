import uuid
import hashlib


def generate_verification_code() -> str:
    return hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()[::2]
