from sqlalchemy import Column, BigInteger, String, Integer, DateTime, ForeignKey, Index, DECIMAL
from sqlalchemy.sql import func

from entity.base_model import Base


class OrderItem(Base):
    """Order items with snapshotted product data"""
    __tablename__ = 'OrderItems'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    order_id = Column(BigInteger, ForeignKey('Orders.id', ondelete='CASCADE'), nullable=False)
    product_id = Column(BigInteger, ForeignKey('Products.id', ondelete='RESTRICT'), nullable=False)

    product_name = Column(String(255), nullable=False)
    product_sku = Column(String(100))
    unit_price = Column(DECIMAL(10, 2), nullable=False)
    quantity = Column(Integer, default=1, nullable=False)
    total_price = Column(DECIMAL(15, 2), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), default=func.now(), nullable=False)
    
    __table_args__ = (
        Index('idx_item_order', 'order_id'),
        Index('idx_item_product', 'product_id'),
    )

