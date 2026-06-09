from sqlalchemy import Column, BigInteger, String, Integer, Boolean, DateTime, ForeignKey, Index, JSON

from models.base_model import Base, TimestampMixin, ActiveMixin


class APIKey(Base, TimestampMixin, ActiveMixin):
    """API Keys for retail partner integrations"""
    __tablename__ = 'APIKeys'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    key_hash = Column(String(255), nullable=False, unique=True, index=True)
    key_prefix = Column(String(20), nullable=False)
    owner_user_id = Column(BigInteger, ForeignKey('Users.id', ondelete='SET NULL'))
    
    scopes = Column(JSON)
    rate_limit_rpm = Column(Integer, default=100, nullable=False)
    is_active = Column(Boolean, default=True, index=True)
    last_used_at = Column(DateTime(6))
    expires_at = Column(DateTime(6))
    
    __table_args__ = (
        Index('idx_apikey_hash', 'key_hash'),
        Index('idx_apikey_active', 'is_active'),
    )

