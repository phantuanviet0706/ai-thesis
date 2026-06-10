from sqlalchemy import Column, BigInteger, String, Text, DateTime, ForeignKey, Index, DECIMAL

from entity.base_model import Base, TimestampMixin


class Order(Base, TimestampMixin):
    """Orders with conversation session tracking"""
    __tablename__ = 'Orders'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    order_code = Column(String(50), nullable=False, unique=True, index=True)
    user_id = Column(BigInteger, ForeignKey('Users.id', ondelete='SET NULL'))
    shipping_address_id = Column(BigInteger, ForeignKey('UserAddresses.id'))

    subtotal = Column(DECIMAL(15, 2), default=0.00, nullable=False)
    discount_amount = Column(DECIMAL(15, 2), default=0.00, nullable=False)
    shipping_fee = Column(DECIMAL(15, 2), default=0.00, nullable=False)
    total_amount = Column(DECIMAL(15, 2), default=0.00, nullable=False)

    status = Column(String(50), default='pending', nullable=False, index=True)  # pending, confirmed, processing, shipped, delivered, cancelled, refunded
    payment_status = Column(String(50), default='unpaid', nullable=False, index=True)  # unpaid, paid, partial, refunded

    shipping_method = Column(String(100))
    tracking_number = Column(String(100))
    notes = Column(Text)
    staff_notes = Column(Text)

    conversation_session_id = Column(BigInteger, ForeignKey('ConversationSessions.id', ondelete='SET NULL'), index=True)

    confirmed_at = Column(DateTime(6))
    shipped_at = Column(DateTime(6))
    delivered_at = Column(DateTime(6))
    cancelled_at = Column(DateTime(6))

    __table_args__ = (
        Index('idx_order_code', 'order_code'),
        Index('idx_order_user', 'user_id'),
        Index('idx_order_status', 'status'),
        Index('idx_order_payment', 'payment_status'),
        Index('idx_order_created', 'created_at'),
        Index('idx_order_session', 'conversation_session_id'),
    )

