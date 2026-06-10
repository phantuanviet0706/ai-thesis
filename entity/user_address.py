from sqlalchemy import Column, BigInteger, String, Boolean, ForeignKey, Index

from entity.base_model import Base, TimestampMixin


class UserAddress(Base, TimestampMixin):
    """User address for multi-address checkout"""
    __tablename__ = 'UserAddresses'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey('Users.id', ondelete='CASCADE'), nullable=False)
    
    label = Column(String(100))  # Nhà, Văn phòng
    recipient_name = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=False)
    address_line1 = Column(String(255), nullable=False)
    address_line2 = Column(String(255))
    ward = Column(String(100))
    district = Column(String(100))
    province = Column(String(100), nullable=False)
    is_default = Column(Boolean, default=False)
    
    __table_args__ = (
        Index('idx_address_user', 'user_id'),
        Index('idx_address_default', 'user_id', 'is_default'),
    )

