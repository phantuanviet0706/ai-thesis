from sqlalchemy import Column, BigInteger, String, Text, Integer, ForeignKey, Index

from models.base_model import Base, TimestampMixin


class ConversationMessage(Base, TimestampMixin):
    """Full conversation message log (durable record)"""
    __tablename__ = 'ConversationMessages'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(BigInteger, ForeignKey('ConversationSessions.id', ondelete='CASCADE'), nullable=False)
    turn_number = Column(Integer, nullable=False)
    role = Column(String(50), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    
    agent_name = Column(String(50))  # orchestrator, kr_agent, psych_agent, synth_agent.md
    latency_ms = Column(Integer)
    token_count = Column(Integer)
    
    __table_args__ = (
        Index('idx_msg_session', 'session_id'),
        Index('idx_msg_turn', 'session_id', 'turn_number'),
        Index('idx_msg_agent', 'agent_name'),
    )

