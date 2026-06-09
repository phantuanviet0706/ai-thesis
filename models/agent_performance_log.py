from sqlalchemy import Column, BigInteger, String, Integer, ForeignKey, Index, JSON, DECIMAL

from models.base_model import Base, TimestampMixin


class AgentPerformanceLog(Base, TimestampMixin):
    """Agent performance logs (latency, tokens, retrieval metrics)"""
    __tablename__ = 'AgentPerformanceLogs'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(BigInteger, ForeignKey('ConversationSessions.id', ondelete='CASCADE'), nullable=False)
    turn_number = Column(Integer, nullable=False)
    agent_name = Column(String(50), nullable=False)

    latency_ms = Column(Integer, nullable=False)
    input_tokens = Column(Integer)
    output_tokens = Column(Integer)
    retrieval_score = Column(DECIMAL(5, 4))
    retrieved_product_ids = Column(JSON)
    error_message = Column(String(500))


    __table_args__ = (
        Index('idx_perf_session', 'session_id'),
        Index('idx_perf_agent', 'agent_name'),
        Index('idx_perf_latency', 'latency_ms'),
    )

