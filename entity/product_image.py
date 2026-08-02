from sqlalchemy import Column, BigInteger, String, Integer, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.sql import func

from entity.base_model import Base


class ProductImage(Base):
    """Product images with primary indicator and sort order"""
    __tablename__ = 'ProductImages'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    product_id = Column(BigInteger, ForeignKey('Products.id', ondelete='CASCADE'), nullable=False)

    url = Column(String(500), nullable=False)
    alt_text = Column(String(255))
    sort_order = Column(Integer, default=0, nullable=False)
    is_primary = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now(), default=func.now(), nullable=False)


    __table_args__ = (
        Index('idx_image_product', 'product_id'),
        Index('idx_image_primary', 'product_id', 'is_primary'),
    )

