from sqlalchemy import Column, BigInteger, String, Integer, Boolean, ForeignKey, Index

from entity.base_model import Base, TimestampMixin


class ProductImage(Base, TimestampMixin):
    """Product images with primary indicator and sort order"""
    __tablename__ = 'ProductImages'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    product_id = Column(BigInteger, ForeignKey('Products.id', ondelete='CASCADE'), nullable=False)

    url = Column(String(500), nullable=False)
    alt_text = Column(String(255))
    sort_order = Column(Integer, default=0, nullable=False)
    is_primary = Column(Boolean, default=False)


    __table_args__ = (
        Index('idx_image_product', 'product_id'),
        Index('idx_image_primary', 'product_id', 'is_primary'),
    )

