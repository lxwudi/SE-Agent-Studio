from __future__ import annotations

from sqlalchemy import BigInteger
from sqlalchemy import Integer
from sqlalchemy.orm import DeclarativeBase


BIGINT_PK = BigInteger().with_variant(Integer, "sqlite")


class Base(DeclarativeBase):
    pass

