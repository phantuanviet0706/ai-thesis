from sqlalchemy import Column, BigInteger, String, DateTime, ForeignKey, Index

from entity.base_model import Base, TimestampMixin


class Cart(Base, TimestampMixin):
    """Persistent cart supporting logged-in and guest users"""
    __tablename__ = 'Carts'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey('Users.id', ondelete='CASCADE'))
    session_key = Column(String(255), index=True)
    expires_at = Column(DateTime, index=True)

    __table_args__ = (
        Index('idx_cart_user', 'user_id'),
        Index('idx_cart_session', 'session_key'),
        Index('idx_cart_expires', 'expires_at'),
    )

