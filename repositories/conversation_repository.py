from datetime import datetime

from sqlalchemy.orm import Session

from core.logger import custom_logger
from entity import ConversationMessage
from entity.conversation_session import ConversationSession


class ConversationRepository:
    def __init__(self, db: Session):
        """
        @desc Khởi tạo repository quản lý hội thoại với phiên làm việc cơ sở dữ liệu
        @params db (Session): Phiên làm việc SQLAlchemy dùng để thao tác với cơ sở dữ liệu
        """
        self.db = db

    def upsert_session(
        self,
        thread_id: str,
        user_id: int | None,
        channel: str,
    ) -> ConversationSession:
        """
        @desc Trả về phiên hội thoại hiện có hoặc tạo mới nếu chưa tồn tại cho thread_id tương ứng
        @params thread_id (str): Mã định danh duy nhất của luồng hội thoại
        @params user_id (int | None): ID của người dùng liên kết với phiên hội thoại, có thể là None nếu chưa đăng nhập
        @params channel (str): Kênh giao tiếp khởi tạo phiên hội thoại (ví dụ: web, api)
        @return ConversationSession: Đối tượng phiên hội thoại hiện có hoặc vừa được tạo mới
        """
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
            self.db.flush()
            custom_logger.info(
                f"[ConvRepo] New session created | thread_id={thread_id} | "
                f"channel={channel} | user_id={user_id}"
            )
        else:
            custom_logger.debug(
                f"[ConvRepo] Existing session recovered | thread_id={thread_id} | "
                f"turns={session.total_turns}"
            )
        return session

    def update_session_after_turn(
        self,
        session: ConversationSession,
        psych_state: str | None,
        consult_strategy: str | None,
        iteration_count: int,
    ) -> None:
        """
        @desc Cập nhật thông tin phiên hội thoại sau mỗi lượt trao đổi, bao gồm trạng thái tâm lý, chiến lược tư vấn và số lượt lặp
        @params session (ConversationSession): Đối tượng phiên hội thoại cần cập nhật
        @params psych_state (str | None): Trạng thái tâm lý cuối cùng được phân tích, có thể là None
        @params consult_strategy (str | None): Chiến lược tư vấn được áp dụng, có thể là None
        @params iteration_count (int): Số lần lặp xử lý trong lượt hiện tại
        """
        session.final_psych_state = psych_state
        session.final_consult_strategy = consult_strategy
        session.iteration_count = iteration_count
        session.total_turns = (session.total_turns or 0) + 1
        session.last_active_at = datetime.utcnow()
        custom_logger.debug(
            f"[ConvRepo] Session updated | id={session.id} | "
            f"turns={session.total_turns} | psych={psych_state}"
        )

    def log_message(
        self,
        session_id: int,
        turn_number: int,
        role: str,
        content: str,
        agent_name: str | None = None,
        latency_ms: int | None = None,
    ) -> None:
        """
        @desc Ghi lại một tin nhắn trong lượt hội thoại vào cơ sở dữ liệu
        @params session_id (int): ID của phiên hội thoại chứa tin nhắn
        @params turn_number (int): Số thứ tự lượt trao đổi trong phiên
        @params role (str): Vai trò của người gửi tin nhắn (ví dụ: user, assistant)
        @params content (str): Nội dung văn bản của tin nhắn
        @params agent_name (str | None): Tên agent xử lý tin nhắn này, có thể là None (tuỳ chọn)
        @params latency_ms (int | None): Thời gian xử lý tin nhắn tính bằng mili giây, có thể là None (tuỳ chọn)
        """
        msg = ConversationMessage(
            session_id=session_id,
            turn_number=turn_number,
            role=role,
            content=content,
            agent_name=agent_name,
            latency_ms=latency_ms,
        )
        self.db.add(msg)
        custom_logger.debug(
            f"[ConvRepo] Message logged | session={session_id} | turn={turn_number} | "
            f"role={role} | agent={agent_name} | content_len={len(content)}"
        )
