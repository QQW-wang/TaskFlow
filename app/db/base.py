"""SQLAlchemy 声明式基类。

所有 ORM 模型都继承 Base，Alembic 通过 Base.metadata 发现表结构。
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass