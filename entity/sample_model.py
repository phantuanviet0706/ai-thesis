from sqlalchemy import Column, BigInteger, String, Text, Boolean

from entity.base_model import Base, TimestampMixin, ActiveMixin, SystemScopedMixin


class SampleModel(Base, TimestampMixin, ActiveMixin, SystemScopedMixin):
    __tablename__ = 'SampleModels'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(255))
    type = Column(String(50))
    description = Column(Text)
    is_active = Column(Boolean, default=True)
