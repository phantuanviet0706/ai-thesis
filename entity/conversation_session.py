from sqlalchemy import Column, BigInteger, String, Integer, DateTime, ForeignKey, Index
from sqlalchemy.sql import func

from entity.base_model import Base


class ConversationSession(Base):
    """Conversation sessions linked to LangGraph thread_id"""
    __tablename__ = 'ConversationSessions'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    thread_id = Column(String(36), nullable=False, unique=True, index=True)
    user_id = Column(BigInteger, ForeignKey('Users.id', ondelete='SET NULL'))
    channel = Column(String(50), default='web', nullable=False, index=True)  # web, mobile, facebook, zalo, tiktok
    status = Column(String(50), default='active', nullable=False, index=True)  # active, completed, abandoned, error

    final_psych_state = Column(String(50))
    final_consult_strategy = Column(String(100))
    total_turns = Column(Integer, default=0, nullable=False)
    iteration_count = Column(Integer, default=0, nullable=False)

    conversion_outcome = Column(String(50), default='no_intent', nullable=False, index=True)  # no_intent, expressed_interest, added_to_cart, purchased
    linked_order_id = Column(BigInteger, ForeignKey('Orders.id', ondelete='SET NULL'))

    started_at = Column(DateTime(6), default=func.now(), nullable=False)
    last_active_at = Column(DateTime(6), default=func.now(), nullable=False, index=True)
    ended_at = Column(DateTime(6))

    __table_args__ = (
        Index('idx_session_thread', 'thread_id'),
        Index('idx_session_user', 'user_id'),
        Index('idx_session_status', 'status'),
        Index('idx_session_channel', 'channel'),
        Index('idx_session_outcome', 'conversion_outcome'),
        Index('idx_session_active', 'last_active_at'),
    )

