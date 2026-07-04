"""
BusinessService — xử lý toàn bộ side-effects sau mỗi lượt hội thoại:

  1. Ghi PsychStateLogs + AgentPerformanceLogs (ML training data)
  2. Upsert User + UserProfile từ thông tin trích xuất
  3. Tạo Order + OrderItems khi khách xác nhận mua
  4. Cập nhật ConversationSession.conversion_outcome
  5. Upsert ChromaDB training_conversations + training_psych_labels (per-turn)
  6. Upsert ChromaDB training_sessions_success (full session khi sale thành công)

Tất cả chạy async background — không ảnh hưởng latency response.
"""

import asyncio
import json
import re
import uuid
from typing import Any

from core.logger import custom_logger
from database import get_db
from database.vector_db_manager import VectorDBManager
from repositories.business_repository import BusinessRepository
from repositories.conversation_repository import ConversationRepository
from retrieval.embeddings import embed_documents
from constants.constants import (
    COLLECTION_TRAINING_CONV,
    COLLECTION_TRAINING_PSYCH,
    COLLECTION_TRAINING_SUCCESS,
)


_VN_PHONE_RE = re.compile(r"^(0|\+84)[3-9]\d{8}$")


def _sanitize_extracted_info(extracted: dict | None) -> dict | None:
    """
    Validate và làm sạch các trường do LLM extract trước khi persist xuống DB.
    Loại bỏ dữ liệu không hợp lệ thay vì để crash ở tầng repository.
    """
    if not extracted:
        return extracted

    result = dict(extracted)

    # Phone — phải là số điện thoại VN hợp lệ
    phone = str(result.get("customer_phone") or "").strip()
    if phone and not _VN_PHONE_RE.match(phone):
        custom_logger.warning(f"[BizService] Invalid phone discarded: '{phone}'")
        result["customer_phone"] = None

    # Birth year — phải trong khoảng hợp lý
    birth_year = result.get("birth_year")
    if birth_year is not None:
        try:
            birth_year = int(birth_year)
            if not (1900 < birth_year < 2020):
                custom_logger.warning(f"[BizService] Invalid birth_year discarded: {birth_year}")
                result["birth_year"] = None
        except (TypeError, ValueError):
            result["birth_year"] = None

    # Confidence — clamp về [0.0, 1.0]
    try:
        result["confidence"] = max(0.0, min(1.0, float(result.get("confidence", 0.0))))
    except (TypeError, ValueError):
        result["confidence"] = 0.0

    return result


class BusinessService:

    async def process_turn_async(
        self,
        session_id: str,
        user_message: str,
        final_response: str,
        psych_state: str | None,
        psych_confidence: float,
        primary_concern: str | None,
        consult_strategy: str | None,
        extracted_info: dict | None,
        retrieved_product_ids: list[str],
        top_retrieval_score: float,
        latency_ms: int,
        turn_number: int,
        pre_created_order_id: int | None = None,
        session_transcript: list[tuple[str, str]] | None = None,
    ) -> None:
        """
        @desc Entry point bất đồng bộ — gọi toàn bộ pipeline lưu trữ dữ liệu kinh doanh và ML
        """
        try:
            await asyncio.to_thread(
                self._process_turn_sync,
                session_id, user_message, final_response,
                psych_state, psych_confidence, primary_concern, consult_strategy,
                extracted_info, retrieved_product_ids, top_retrieval_score,
                latency_ms, turn_number, pre_created_order_id, session_transcript,
            )
        except Exception as exc:
            custom_logger.warning(
                f"[BizService] process_turn failed | session={session_id} | error={exc}"
            )

    def _process_turn_sync(
        self,
        session_id: str,
        user_message: str,
        final_response: str,
        psych_state: str | None,
        psych_confidence: float,
        primary_concern: str | None,
        consult_strategy: str | None,
        extracted_info: dict | None,
        retrieved_product_ids: list[str],
        top_retrieval_score: float,
        latency_ms: int,
        turn_number: int,
        pre_created_order_id: int | None = None,
        session_transcript: list[tuple[str, str]] | None = None,
    ) -> None:
        extracted_info = _sanitize_extracted_info(extracted_info)

        with get_db() as db:
            conv_repo = ConversationRepository(db)
            biz_repo = BusinessRepository(db)

            session = conv_repo.upsert_session(session_id, user_id=None, channel="chatbot")

            # 1. ML logs
            if psych_state:
                biz_repo.log_psych_state(
                    session_db_id=session.id,
                    turn_number=turn_number,
                    psych_state=psych_state,
                    confidence=psych_confidence,
                    primary_concern=primary_concern,
                    consult_strategy=consult_strategy,
                    raw_output=extracted_info,
                )
            biz_repo.log_agent_performance(
                session_db_id=session.id,
                turn_number=turn_number,
                agent_name="pipeline",
                latency_ms=latency_ms,
                retrieval_score=top_retrieval_score if top_retrieval_score > 0 else None,
                retrieved_product_ids=retrieved_product_ids or None,
            )

            # 2. User / Profile từ thông tin trích xuất
            user_id = session.user_id
            if extracted_info:
                phone = extracted_info.get("customer_phone")
                name = extracted_info.get("customer_name")

                if phone:
                    user = biz_repo.upsert_user_by_phone(phone, name)
                    user_id = user.id
                    if not session.user_id:
                        session.user_id = user_id
                    biz_repo.update_user_profile(user_id, extracted_info)

            # 3. Order — bỏ qua nếu đã tạo đồng bộ ở chat_service (pre_created_order_id có sẵn)
            # Chỉ tạo đơn dự phòng khi đã đủ điều kiện "purchased" (sản phẩm + SĐT) — tránh tạo đơn
            # thật chỉ vì order_intent=true ở giai đoạn added_to_cart (chưa đủ thông tin giao hàng)
            order_id = pre_created_order_id
            if (
                not pre_created_order_id
                and extracted_info
                and extracted_info.get("order_intent")
                and extracted_info.get("conversion_outcome") == "purchased"
                and extracted_info.get("customer_phone")
            ):
                selected = self._resolve_selected_products(
                    extracted_info.get("selected_product_ids", []),
                )
                if selected:
                    order = biz_repo.create_order_from_chat(
                        session_db_id=session.id,
                        user_id=user_id,
                        selected_products=selected,
                        notes=f"Đặt qua chatbot | session={session_id}",
                    )
                    if order:
                        order_id = order.id

            # 4. Cập nhật conversion_outcome
            outcome = (extracted_info or {}).get("conversion_outcome", "no_intent")
            biz_repo.update_session_outcome(session, outcome, order_id)

            db.flush()

        # 5. ChromaDB per-turn training data (outside DB transaction)
        if final_response:
            self._upsert_training_data(
                session_id=session_id,
                turn_number=turn_number,
                user_message=user_message,
                final_response=final_response,
                psych_state=psych_state or "UNKNOWN",
                conversion_outcome=outcome,
                retrieved_product_ids=retrieved_product_ids,
            )

        # 6. ChromaDB session-level training data khi sale thành công
        if order_id and session_transcript:
            self._upsert_session_success_training(
                session_id=session_id,
                session_transcript=session_transcript,
                psych_state=psych_state or "UNKNOWN",
                retrieved_product_ids=retrieved_product_ids,
                turn_number=turn_number,
            )

        custom_logger.info(
            f"[BizService] turn processed | session={session_id} | "
            f"outcome={outcome} | order={'yes' if order_id else 'no'}"
        )

    def _resolve_selected_products(
        self,
        selected_ids: list[str],
    ) -> list[dict]:
        """
        @desc Ghép ID sản phẩm được chọn với thông tin cơ bản để tạo OrderItem
        Chỉ dùng sản phẩm khách đã CHỌN RÕ RÀNG (theo Extraction Agent) — không đoán/fallback
        sang sản phẩm đầu tiên retrieved, vì retrieval chỉ phản ánh ngữ cảnh tư vấn, không phải lựa chọn mua.
        """
        return [
            {"product_id": pid, "name": f"Sản phẩm #{pid}", "price": 0, "quantity": 1}
            for pid in selected_ids
            if pid
        ]

    def _upsert_training_data(
        self,
        session_id: str,
        turn_number: int,
        user_message: str,
        final_response: str,
        psych_state: str,
        conversion_outcome: str,
        retrieved_product_ids: list[str],
    ) -> None:
        """
        @desc Upsert cặp (user_query, bot_response) vào ChromaDB để dùng làm dữ liệu huấn luyện
        """
        try:
            vdb = VectorDBManager()
            doc_id = f"turn_{session_id}_{turn_number}"

            # training_conversations: cặp hội thoại đầy đủ
            conv_text = f"[Khách]: {user_message}\n[Bot]: {final_response}"
            conv_meta = {
                "session_id": session_id,
                "turn_number": turn_number,
                "psych_state": psych_state,
                "conversion_outcome": conversion_outcome,
                "product_ids": json.dumps(retrieved_product_ids),
            }
            conv_col = vdb.get_collection(COLLECTION_TRAINING_CONV)
            conv_vecs = embed_documents([conv_text])
            conv_col.upsert(ids=[doc_id], documents=[conv_text], embeddings=conv_vecs, metadatas=[conv_meta])

            # training_psych_labels: chỉ lưu user message + label tâm lý
            psych_text = user_message
            psych_meta = {
                "session_id": session_id,
                "turn_number": turn_number,
                "psych_label": psych_state,
                "conversion_outcome": conversion_outcome,
            }
            psych_col = vdb.get_collection(COLLECTION_TRAINING_PSYCH)
            psych_vecs = embed_documents([psych_text])
            psych_col.upsert(
                ids=[f"psych_{doc_id}"],
                documents=[psych_text],
                embeddings=psych_vecs,
                metadatas=[psych_meta],
            )

        except Exception as exc:
            custom_logger.warning(f"[BizService] ChromaDB per-turn training upsert failed: {exc}")

    def _upsert_session_success_training(
        self,
        session_id: str,
        session_transcript: list[tuple[str, str]],
        psych_state: str,
        retrieved_product_ids: list[str],
        turn_number: int,
    ) -> None:
        """
        @desc Lưu toàn bộ transcript của phiên hội thoại thành công vào ChromaDB training_sessions_success.
        Data này được Synth Agent truy xuất làm few-shot example cho các query tương tự trong tương lai.
        """
        try:
            # Xây dựng transcript hoàn chỉnh theo lượt
            lines: list[str] = []
            turn_idx = 0
            i = 0
            while i < len(session_transcript):
                role, content = session_transcript[i]
                if role == "user":
                    turn_idx += 1
                    lines.append(f"[Lượt {turn_idx}]")
                    lines.append(f"Khách: {content}")
                    # Bot response ngay sau
                    if i + 1 < len(session_transcript) and session_transcript[i + 1][0] == "assistant":
                        lines.append(f"Tư vấn viên: {session_transcript[i + 1][1]}")
                        i += 2
                        continue
                i += 1

            lines.append("[KẾT THÚC: Đặt hàng thành công ✓]")
            transcript_text = "\n".join(lines)

            # Dùng đoạn đầu transcript làm search vector (ngữ cảnh mua hàng của khách)
            search_anchor = "\n".join(
                content for role, content in session_transcript[:6] if role == "user"
            ) or transcript_text[:300]

            doc_id = f"success_{session_id}"
            meta = {
                "session_id": session_id,
                "psych_final": psych_state,
                "turn_count": turn_number,
                "product_ids": json.dumps(retrieved_product_ids),
                "outcome": "purchase_confirmed",
            }

            vdb = VectorDBManager()
            col = vdb.get_collection(COLLECTION_TRAINING_SUCCESS)
            vecs = embed_documents([search_anchor])
            col.upsert(ids=[doc_id], documents=[transcript_text], embeddings=vecs, metadatas=[meta])

            custom_logger.info(
                f"[BizService] session success training saved | session={session_id} | "
                f"turns={turn_number} | psych_final={psych_state}"
            )
        except Exception as exc:
            custom_logger.warning(f"[BizService] ChromaDB session success upsert failed: {exc}")
