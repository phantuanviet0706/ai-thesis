"""
BusinessRepository — ghi nhận dữ liệu kinh doanh và ML từ mỗi lượt hội thoại.

Xử lý:
  - Upsert User + UserProfile từ thông tin khách cung cấp qua chat
  - Tạo Order + OrderItems khi khách xác nhận mua
  - Cập nhật ConversationSession.conversion_outcome
  - Ghi PsychStateLogs + AgentPerformanceLogs cho ML
"""

import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from core.logger import custom_logger
from entity.agent_performance_log import AgentPerformanceLog
from entity.conversation_session import ConversationSession
from entity.order import Order
from entity.order_item import OrderItem
from entity.psych_state_log import PsychStateLog
from entity.user import User
from entity.user_profile import UserProfile


class BusinessRepository:
    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # User / Profile
    # ------------------------------------------------------------------

    def upsert_user_by_phone(self, phone: str, name: str | None) -> User:
        """
        @desc Tìm hoặc tạo User theo số điện thoại, cập nhật tên nếu có
        @params phone (str): Số điện thoại khách hàng
        @params name (str | None): Tên khách hàng nếu có
        @return User: Đối tượng User tìm thấy hoặc vừa tạo
        """
        user = self.db.query(User).filter_by(phone=phone).first()
        if user is None:
            user = User(
                phone=phone,
                role="customer",
                is_active=True,
                is_verified=False,
                auth_provider="chatbot",
            )
            self.db.add(user)
            self.db.flush()
            custom_logger.info(f"[BizRepo] New user created | phone={phone}")
        return user

    def update_user_profile(self, user_id: int, extracted: dict) -> None:
        """
        @desc Upsert UserProfile với thông tin trích xuất từ hội thoại (chỉ ghi đè khi có giá trị mới)
        @params user_id (int): ID của User cần cập nhật profile
        @params extracted (dict): Dict thông tin trích xuất từ Extraction Agent
        """
        profile = self.db.query(UserProfile).filter_by(user_id=user_id).first()
        if profile is None:
            profile = UserProfile(user_id=user_id)
            self.db.add(profile)
            self.db.flush()

        if extracted.get("customer_name"):
            profile.display_name = extracted["customer_name"]
        if extracted.get("zodiac_sign"):
            profile.zodiac_sign = extracted["zodiac_sign"]
        if extracted.get("gender"):
            profile.gender = extracted["gender"]
        if extracted.get("birth_year") and not profile.date_of_birth:
            from datetime import date
            profile.date_of_birth = date(int(extracted["birth_year"]), 1, 1)

        new_prefs = extracted.get("preferences") or {}
        if new_prefs:
            current = profile.preferences or {}
            profile.preferences = {**current, **new_prefs}

        custom_logger.debug(f"[BizRepo] UserProfile updated | user_id={user_id}")

    # ------------------------------------------------------------------
    # Order
    # ------------------------------------------------------------------

    def create_order_from_chat(
        self,
        session_db_id: int,
        user_id: int | None,
        selected_products: list[dict],
        notes: str | None = None,
    ) -> Order | None:
        """
        @desc Tạo Order + OrderItems từ sản phẩm khách chọn trong hội thoại
        @params session_db_id (int): ID bản ghi ConversationSession trong DB
        @params user_id (int | None): ID User đặt hàng, None nếu là khách vãng lai
        @params selected_products (list[dict]): Danh sách {"product_id", "name", "sku", "price", "quantity"}
        @params notes (str | None): Ghi chú thêm từ hội thoại
        @return Order | None: Đối tượng Order vừa tạo, hoặc None nếu không có sản phẩm
        """
        if not selected_products:
            return None

        subtotal = sum(
            float(p.get("price", 0)) * int(p.get("quantity", 1))
            for p in selected_products
        )
        order_code = f"CHAT-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

        order = Order(
            order_code=order_code,
            user_id=user_id,
            subtotal=subtotal,
            total_amount=subtotal,
            status="pending",
            payment_status="unpaid",
            notes=notes,
            conversation_session_id=session_db_id,
        )
        self.db.add(order)
        self.db.flush()

        for p in selected_products:
            qty = int(p.get("quantity", 1))
            price = float(p.get("price", 0))
            item = OrderItem(
                order_id=order.id,
                product_id=int(p["product_id"]),
                product_name=p.get("name", ""),
                product_sku=p.get("sku"),
                unit_price=price,
                quantity=qty,
                total_price=price * qty,
            )
            self.db.add(item)

        custom_logger.info(
            f"[BizRepo] Order created | code={order_code} | "
            f"items={len(selected_products)} | total={subtotal:,.0f}₫"
        )
        return order

    def get_orders_by_session_thread(self, thread_id: str) -> list:
        """
        @desc Lấy danh sách Order liên kết với ConversationSession theo thread_id
        @params thread_id (str): LangGraph thread_id của phiên hội thoại
        @return list[Order]: Danh sách đơn hàng, mới nhất trước
        """
        session = (
            self.db.query(ConversationSession)
            .filter_by(thread_id=thread_id)
            .first()
        )
        if not session:
            return []
        return (
            self.db.query(Order)
            .filter_by(conversation_session_id=session.id)
            .order_by(Order.id.desc())
            .all()
        )

    # ------------------------------------------------------------------
    # ConversationSession outcome
    # ------------------------------------------------------------------

    def update_session_outcome(
        self,
        session: ConversationSession,
        conversion_outcome: str,
        order_id: int | None = None,
    ) -> None:
        """
        @desc Cập nhật kết quả chuyển đổi của session và link order nếu có
        @params session (ConversationSession): Đối tượng session cần cập nhật
        @params conversion_outcome (str): Kết quả: no_intent | expressed_interest | added_to_cart | purchased
        @params order_id (int | None): ID Order nếu khách đã đặt hàng
        """
        _rank = {"no_intent": 0, "expressed_interest": 1, "added_to_cart": 2, "purchased": 3}
        current_rank = _rank.get(session.conversion_outcome or "no_intent", 0)
        new_rank = _rank.get(conversion_outcome, 0)

        if new_rank > current_rank:
            session.conversion_outcome = conversion_outcome
        if order_id:
            session.linked_order_id = order_id

    # ------------------------------------------------------------------
    # ML logging
    # ------------------------------------------------------------------

    def log_psych_state(
        self,
        session_db_id: int,
        turn_number: int,
        psych_state: str,
        confidence: float,
        primary_concern: str | None,
        consult_strategy: str | None,
        raw_output: dict | None,
    ) -> None:
        """
        @desc Ghi log trạng thái tâm lý khách hàng theo từng lượt hội thoại
        @params session_db_id (int): ID bản ghi ConversationSession
        @params turn_number (int): Số thứ tự lượt hội thoại
        @params psych_state (str): Trạng thái tâm lý (CURIOUS, INTERESTED, v.v.)
        @params confidence (float): Độ tin cậy phân loại [0.0, 1.0]
        @params primary_concern (str | None): Mối quan tâm chính của khách
        @params consult_strategy (str | None): Chiến lược tư vấn được chọn
        @params raw_output (dict | None): JSON thô từ Psych Agent
        """
        self.db.add(PsychStateLog(
            session_id=session_db_id,
            turn_number=turn_number,
            psych_state=psych_state,
            confidence_score=min(1.0, max(0.0, confidence)),
            primary_concern=primary_concern,
            consult_strategy=consult_strategy,
            raw_output=raw_output,
        ))

    def log_agent_performance(
        self,
        session_db_id: int,
        turn_number: int,
        agent_name: str,
        latency_ms: int,
        retrieval_score: float | None = None,
        retrieved_product_ids: list | None = None,
        error_message: str | None = None,
    ) -> None:
        """
        @desc Ghi log hiệu suất agent theo từng lượt hội thoại để theo dõi và huấn luyện mô hình
        @params session_db_id (int): ID bản ghi ConversationSession
        @params turn_number (int): Số thứ tự lượt hội thoại
        @params agent_name (str): Tên agent (orchestrator, kr_agent, psych_agent, synth_agent)
        @params latency_ms (int): Thời gian xử lý tính bằng millisecond
        @params retrieval_score (float | None): Điểm retrieval cao nhất (chỉ dùng cho KR Agent)
        @params retrieved_product_ids (list | None): Danh sách ID sản phẩm đã truy xuất
        @params error_message (str | None): Thông báo lỗi nếu có
        """
        self.db.add(AgentPerformanceLog(
            session_id=session_db_id,
            turn_number=turn_number,
            agent_name=agent_name,
            latency_ms=latency_ms,
            retrieval_score=retrieval_score,
            retrieved_product_ids=retrieved_product_ids,
            error_message=error_message,
        ))
