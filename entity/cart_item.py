from sqlalchemy import Column, BigInteger, Integer, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.sql import func

from entity.base_model import Base


class CartItem(Base):
    """Cart items"""
    __tablename__ = 'CartItems'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    cart_id = Column(BigInteger, ForeignKey('Carts.id', ondelete='CASCADE'), nullable=False)
    product_id = Column(BigInteger, ForeignKey('Products.id', ondelete='CASCADE'), nullable=False)
    quantity = Column(Integer, default=1, nullable=False)

    added_at = Column(DateTime(6), default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint('cart_id', 'product_id', name='uq_cart_product'),
        Index('idx_cartitem_cart', 'cart_id'),
    )

