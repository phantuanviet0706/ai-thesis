from sqlalchemy import Column, BigInteger, String, DateTime, ForeignKey, Index, JSON, DECIMAL
from sqlalchemy.sql import func

from entity.base_model import Base


class Payment(Base):
    """Payments with multiple attempts support"""
    __tablename__ = 'Payments'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    order_id = Column(BigInteger, ForeignKey('Orders.id', ondelete='RESTRICT'), nullable=False)

    payment_method = Column(String(50), nullable=False)  # cod, bank_transfer, momo, vnpay, zalopay, credit_card
    transaction_id = Column(String(255), index=True)
    amount = Column(DECIMAL(15, 2), nullable=False)
    status = Column(String(50), default='pending', nullable=False, index=True)  # pending, success, failed, refunded
    gateway_response = Column(JSON)
    paid_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now(), default=func.now(), nullable=False)

    __table_args__ = (
        Index('idx_payment_order', 'order_id'),
        Index('idx_payment_status', 'status'),
        Index('idx_payment_transaction', 'transaction_id'),
    )

