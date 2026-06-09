from datetime import datetime
from sqlalchemy import Column, BigInteger, DateTime, SmallInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class TimestampMixin:
    created_at = Column(
        DateTime(6),
        default=func.now(),
        nullable=False
    )
    updated_at = Column(
        DateTime(6),
        default=func.now(),
        onupdate=func.now(),
        nullable=False
    )


class SoftDeleteMixin:
    deleted_at = Column(DateTime(6), nullable=True)

    @property
    def is_deleted(self):
        return self.deleted_at is not None

    def soft_delete(self):
        self.deleted_at = datetime.utcnow()

    def restore(self):
        self.deleted_at = None


class ActiveMixin:
    is_active = Column(SmallInteger, default=1, nullable=False)

    def activate(self):
        self.is_active = 1

    def deactivate(self):
        self.is_active = 0