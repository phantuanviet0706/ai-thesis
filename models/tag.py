from sqlalchemy import Column, BigInteger, String, Index

from models.base_model import Base, TimestampMixin


class Tag(Base, TimestampMixin):
    """Tag entity for faceted search (feng_shui, style, occasion, etc.)"""
    __tablename__ = 'Tags'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    slug = Column(String(100), nullable=False, unique=True)
    tag_type = Column(String(50), nullable=False, index=True)

    __table_args__ = (
        Index('idx_tag_type', 'tag_type'),
    )

