from sqlalchemy import Column, BigInteger, String, Text, Integer, ForeignKey, JSON, Index, DECIMAL, Date

from entity.base_model import Base, TimestampMixin


class UserProfile(Base, TimestampMixin):
    """User CRM and personalization data"""
    __tablename__ = 'UserProfiles'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey('Users.id', ondelete='CASCADE'), nullable=False, unique=True)
    
    display_name = Column(String(255))
    avatar_url = Column(String(500))
    date_of_birth = Column(Date)
    gender = Column(String(50))  # male, female, other
    zodiac_sign = Column(String(50), index=True)
    
    preferences = Column(JSON)
    total_orders = Column(Integer, default=0, nullable=False)
    total_spent = Column(DECIMAL(15, 2), default=0.00, nullable=False)
    loyalty_points = Column(Integer, default=0, nullable=False)
    customer_segment = Column(String(50), default='new', index=True)  # new, regular, vip, churned
    staff_notes = Column(Text)
    
    __table_args__ = (
        Index('idx_profile_segment', 'customer_segment'),
        Index('idx_profile_zodiac', 'zodiac_sign'),
    )

