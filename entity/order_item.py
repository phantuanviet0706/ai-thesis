from sqlalchemy import Column, BigInteger, String, Integer, ForeignKey, Index, DECIMAL

from entity.base_model import Base, TimestampMixin


class OrderItem(Base, TimestampMixin):
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
    
    __table_args__ = (
        Index('idx_item_order', 'order_id'),
        Index('idx_item_product', 'product_id'),
    )

