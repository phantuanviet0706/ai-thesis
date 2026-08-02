from sqlalchemy import Column, BigInteger, String, Integer, ForeignKey, Index, JSON, DECIMAL, DateTime
from sqlalchemy.sql import func

from entity.base_model import Base


class PsychStateLog(Base):
    """Psychological state log per turn (CARS Context Consistency metric)"""
    __tablename__ = 'PsychStateLogs'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(BigInteger, ForeignKey('ConversationSessions.id', ondelete='CASCADE'), nullable=False)
    turn_number = Column(Integer, nullable=False)

    psych_state = Column(String(50), nullable=False)  # HESITATION, INTEREST, READY_TO_BUY
    confidence_score = Column(DECIMAL(4, 3), nullable=False)
    primary_concern = Column(String(255))
    consult_strategy = Column(String(500))
    raw_output = Column(JSON)
    created_at = Column(DateTime, server_default=func.now(), default=func.now(), nullable=False)

    __table_args__ = (
        Index('idx_psych_session', 'session_id'),
        Index('idx_psych_state', 'psych_state'),
    )

