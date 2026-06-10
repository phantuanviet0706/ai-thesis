from sqlalchemy import Column, BigInteger, String, Text, Boolean, ForeignKey, Index

from entity.base_model import Base, TimestampMixin


class SystemConfig(Base, TimestampMixin):
    """Runtime feature flags and model parameters"""
    __tablename__ = 'SystemConfigs'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    config_key = Column(String(255), nullable=False, unique=True)
    config_value = Column(Text, nullable=False)
    value_type = Column(String(50), default='string')  # string, integer, float, boolean, json
    description = Column(String(500))
    is_sensitive = Column(Boolean, default=False)
    updated_by = Column(BigInteger, ForeignKey('Users.id', ondelete='SET NULL'))

    __table_args__ = (
        Index('idx_config_key', 'config_key'),
    )

