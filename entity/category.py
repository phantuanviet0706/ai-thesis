from sqlalchemy import Column, BigInteger, String, Text, Boolean, Integer, ForeignKey, Index
from sqlalchemy.orm import relationship

from entity.base_model import Base, TimestampMixin, ActiveMixin


class Category(Base, TimestampMixin, ActiveMixin):
    """Category entity with self-referential hierarchy"""
    __tablename__ = 'Categories'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(Text)
    parent_id = Column(BigInteger, ForeignKey('Categories.id', ondelete='RESTRICT'))
    depth_level = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, index=True)

    # Relationships
    parent = relationship("Category", remote_side=[id], backref="children")

    __table_args__ = (
        Index('idx_category_slug', 'slug'),
        Index('idx_category_parent', 'parent_id'),
        Index('idx_category_active', 'is_active'),
    )

