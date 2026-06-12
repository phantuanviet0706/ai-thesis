from sqlalchemy import Column, BigInteger, String, Boolean, DateTime, Index

from entity.base_model import Base, TimestampMixin, ActiveMixin


class User(Base, TimestampMixin, ActiveMixin):
    """User authentication record"""
    __tablename__ = 'Users'

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    email = Column(String(255), unique=True)
    phone = Column(String(20), unique=True)
    password_hash = Column(String(255))
    auth_provider = Column(String(50))  # local, google, facebook, zalo
    auth_provider_id = Column(String(255))

    role = Column(String(50))  # customer, staff, admin
    is_active = Column(Boolean, default=True, index=True)
    is_verified = Column(Boolean, default=False)

    last_login_at = Column(DateTime)

    __table_args__ = (
        Index('idx_user_email', 'email'),
        Index('idx_user_phone', 'phone'),
        Index('idx_user_role', 'role'),
        Index('idx_user_active', 'is_active'),
    )

