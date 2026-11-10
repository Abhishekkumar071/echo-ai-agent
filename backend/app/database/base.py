"""
SQLAlchemy declarative base shared by all ORM models.
Import Base here — never re-define it in a model file.
"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
