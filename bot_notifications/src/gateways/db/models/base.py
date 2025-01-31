from enum import Enum

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    ...


class TransactionTypes(Enum):
    refill_balance: str = "refill_balance"
    promo: str = "promo"
