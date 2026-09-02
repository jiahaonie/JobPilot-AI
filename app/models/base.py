"""基于 SQLAlchemy 的声明式基类。"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """全部持久化模型的基类。"""
