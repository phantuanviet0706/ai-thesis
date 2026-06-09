from sqlalchemy import Column, BigInteger, String, Index, JSON

from models.base_model import Base, TimestampMixin


class AuditLog(Base, TimestampMixin):
    """Append-only audit logs (never update or delete)"""
    __tablename__ = 'AuditLogs'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    actor_id = Column(BigInteger)
    actor_type = Column(String(50))  # user, system, api_key
    action = Column(String(100), nullable=False)
    resource_type = Column(String(100))
    resource_id = Column(BigInteger)
    old_value = Column(JSON)
    new_value = Column(JSON)
    ip_address = Column(String(45))
    user_agent = Column(String(500))


    __table_args__ = (
        Index('idx_audit_actor', 'actor_id'),
        Index('idx_audit_action', 'action'),
        Index('idx_audit_resource', 'resource_type', 'resource_id'),
        Index('idx_audit_created', 'created_at'),
    )

