"""
Extraction Agent — trích xuất thông tin có cấu trúc từ hội thoại.

Chạy song song với Synth Agent (fan-out từ Orchestrator, xem graph/router.py), không
tham gia vòng routing. Sử dụng Haiku (nhanh, rẻ) vì chỉ cần parsing JSON đơn giản.

Output được lưu vào extracted_info trong ConversationState, sau đó
BusinessService đọc để:
  - Upsert User/UserProfile khi có tên/SĐT
  - Tạo Order + OrderItems khi khách muốn đặt hàng
  - Cập nhật conversion_outcome trong ConversationSession
  - Ghi ChromaDB training collections
"""

from agents.base_agent import BaseLLMAgent
from core.logger import custom_logger
from graph.state import ConversationState, PsychState
from utils.helper import extract_json


def _format_messages_for_extraction(state: ConversationState) -> str:
    messages = state.get("messages", [])
    lines = []
    for msg in messages[-10:]:  # chỉ lấy 10 tin nhắn gần nhất
        role = "Khách" if getattr(msg, "type", "") == "human" else "Bot"
        lines.append(f"[{role}]: {msg.content}")
    return "\n".join(lines) if lines else "(trống)"


def _format_product_list(products: list) -> str:
    if not products:
        return "(không có)"
    return "\n".join(
        f"ID={p.id} | {p.name} | {p.unit_price:,.0f}₫"
        for p in products[:5]
    )


def _format_products_for_context(state: ConversationState) -> str:
    """
    @desc Định dạng sản phẩm thành 2 nhóm tách biệt — lượt hiện tại và lượt trước — để LLM
    resolve đúng selected_product_ids khi khách dùng tham chiếu kiểu "mẫu còn lại"/"cái kia"/
    "sản phẩm thứ 2" trỏ tới thứ đã được gợi ý ở LƯỢT TRƯỚC, không phải kết quả tìm kiếm mới
    (có thể không liên quan) của lượt hiện tại.
    """
    current = state.get("retrieved_products", [])
    previous = state.get("previous_turn_products", [])
    return (
        f"Sản phẩm tìm được LƯỢT NÀY:\n{_format_product_list(current)}\n\n"
        f"Sản phẩm đã gợi ý LƯỢT TRƯỚC:\n{_format_product_list(previous)}"
    )


class ExtractionAgent(BaseLLMAgent):
    prompt_path = "resources/prompt/extraction_agent.md"
    log_tag = "Extraction"
    model_key = "FAST"
    max_tokens = 400

    def build_user_prompt(self, state: ConversationState) -> str:
        conv_text = _format_messages_for_extraction(state)
        products_text = _format_products_for_context(state)
        psych_state = state.get("psych_state", PsychState.CURIOUS)
        return (
            f"Lịch sử hội thoại:\n{conv_text}\n\n"
            f"{products_text}\n\n"
            f"Trạng thái tâm lý hiện tại: {psych_state}"
        )

    def parse_response(self, raw_content: str, state: ConversationState) -> dict:
        extracted = extract_json(raw_content)
        custom_logger.info(
            f"[Extraction] done | outcome={extracted.get('conversion_outcome')} | "
            f"order_intent={extracted.get('order_intent')} | "
            f"wants_image={extracted.get('wants_product_image')} | "
            f"has_phone={bool(extracted.get('customer_phone'))} | "
            f"has_name={bool(extracted.get('customer_name'))}"
        )
        return {
            "extracted_info": extracted,
            # Snapshot retrieved_products của LƯỢT NÀY để lượt sau dùng làm "previous_turn_products"
            # — phải ghi ở ĐÂY (sau khi build_user_prompt của lượt này đã đọc xong giá trị cũ),
            # không ghi ở kr_agent.py vì retrieved_products bị reset về [] mỗi lượt trước khi graph chạy.
            "previous_turn_products": state.get("retrieved_products", []),
        }

    def on_error(self, exc: Exception, state: ConversationState) -> dict:
        # Không set error_state — extraction là side-channel (ghi log/CRM), lỗi ở đây
        # không nên chặn hay ảnh hưởng phản hồi chính cho khách (giữ đúng hành vi gốc).
        custom_logger.warning(f"[Extraction] failed (non-fatal): {exc}")
        return {"extracted_info": None}


extraction_agent_node = ExtractionAgent()
