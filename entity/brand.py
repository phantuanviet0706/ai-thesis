from sqlalchemy import Column, BigInteger, String, Text, Boolean, Index
from entity.base_model import Base, TimestampMixin, ActiveMixin


class Brand(Base, TimestampMixin, ActiveMixin):
    """Brand entity"""
    __tablename__ = 'Brands'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), nullable=False, unique=True, index=True)
    logo_url = Column(String(500))
    description = Column(Text)
    is_active = Column(Boolean, default=True, index=True)

    __table_args__ = (
        Index('idx_brand_slug', 'slug'),
        Index('idx_brand_active', 'is_active'),
    )

