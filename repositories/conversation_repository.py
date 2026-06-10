from datetime import datetime

from sqlalchemy.orm import Session

from entity import ConversationMessage
from entity.conversation_session import ConversationSession


class ConversationRepository:
    def __init__(self, db: Session):
        self.db = db

    def upsert_session(
        self,
        thread_id: str,
        user_id: int | None,
        channel: str,
    ) -> ConversationSession:
        """Return existing session or create a new one for this thread_id."""
        session = (
            self.db.query(ConversationSession)
            .filter_by(thread_id=thread_id)
            .first()
        )
        if session is None:
            session = ConversationSession(
                thread_id=thread_id,
                user_id=user_id,
                channel=channel,
                status="active",
                total_turns=0,
                iteration_count=0,
                started_at=datetime.utcnow(),
                last_active_at=datetime.utcnow(),
            )
            self.db.add(session)
            self.db.flush()  # get session.id before inserting messages
        return session

    def update_session_after_turn(
        self,
        session: ConversationSession,
        psych_state: str | None,
        consult_strategy: str | None,
        iteration_count: int,
    ) -> None:
        session.final_psych_state = psych_state
        session.final_consult_strategy = consult_strategy
        session.iteration_count = iteration_count
        session.total_turns = (session.total_turns or 0) + 1
        session.last_active_at = datetime.utcnow()

    def log_message(
        self,
        session_id: int,
        turn_number: int,
        role: str,
        content: str,
        agent_name: str | None = None,
        latency_ms: int | None = None,
    ) -> None:
        msg = ConversationMessage(
            session_id=session_id,
            turn_number=turn_number,
            role=role,
            content=content,
            agent_name=agent_name,
            latency_ms=latency_ms,
        )
        self.db.add(msg)
