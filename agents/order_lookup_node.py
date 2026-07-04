"""
Order Lookup Node — truy vấn đơn hàng liên kết với phiên chat hiện tại.

Triggered khi Orchestrator phát hiện intent `order_status_check`.
Không dùng LLM — chỉ query DB và format kết quả trực tiếp.
"""

from database import get_db
from entity.conversation_session import ConversationSession
from entity.order import Order
from core.logger import custom_logger
from graph.state import ConversationState

_STATUS_VI = {
    "pending":    "⏳ Chờ xác nhận",
    "confirmed":  "✅ Đã xác nhận",
    "processing": "🔄 Đang xử lý",
    "shipped":    "🚚 Đang giao hàng",
    "delivered":  "📬 Đã giao thành công",
    "cancelled":  "❌ Đã hủy",
    "refunded":   "↩️ Đã hoàn tiền",
}

_PAYMENT_VI = {
    "paid":    "Đã thanh toán ✓",
    "unpaid":  "Chưa thanh toán",
    "partial": "Thanh toán một phần",
    "refunded":"Đã hoàn tiền",
}


def order_lookup_node(state: ConversationState) -> dict:
    """
    @desc Node tra cứu đơn hàng — không dùng LLM, query DB và format response trực tiếp
    @params state (ConversationState): Trạng thái hội thoại chứa session_metadata
    @return dict: State delta gồm final_response với thông tin đơn hàng
    """
    session_id = state.get("session_metadata", {}).get("session_id", "")
    custom_logger.info(f"[OrderLookup] querying orders | session={session_id}")

    try:
        with get_db() as db:
            session = db.query(ConversationSession).filter_by(thread_id=session_id).first()
            if not session:
                return {"final_response": _no_order_response()}

            orders = (
                db.query(Order)
                .filter_by(conversation_session_id=session.id)
                .order_by(Order.id.desc())
                .all()
            )

            if not orders and session.linked_order_id:
                order = db.query(Order).filter_by(id=session.linked_order_id).first()
                if order:
                    orders = [order]

        if not orders:
            return {"final_response": _no_order_response()}

        return {"final_response": _format_orders(orders)}

    except Exception as exc:
        custom_logger.error(f"[OrderLookup] DB error: {exc}", exc_info=True)
        return {
            "final_response": (
                "Xin lỗi, hiện tại em không tra cứu được thông tin đơn hàng. "
                "Bạn vui lòng thử lại sau nhé!"
            )
        }


def _no_order_response() -> str:
    return (
        "Em chưa tìm thấy đơn hàng nào trong phiên chat này ạ.\n"
        "Nếu bạn đã đặt hàng ở phiên trước, vui lòng cung cấp mã đơn hàng "
        "(dạng CHAT-YYYYMMDD-XXXXXX) để em tra cứu chính xác hơn nhé!"
    )


def _format_orders(orders: list) -> str:
    parts = ["Dưới đây là thông tin đơn hàng của bạn:\n"]
    for order in orders:
        status = _STATUS_VI.get(order.status, order.status or "Không xác định")
        payment = _PAYMENT_VI.get(order.payment_status, order.payment_status or "")
        block = (
            f"📦 **Mã đơn hàng:** {order.order_code}\n"
            f"   Trạng thái: {status}\n"
            f"   Tổng tiền: {order.total_amount:,.0f}₫\n"
            f"   Thanh toán: {payment}"
        )
        if order.tracking_number:
            block += f"\n   Mã vận đơn: {order.tracking_number}"
        if order.notes:
            block += f"\n   Ghi chú: {order.notes}"
        parts.append(block)

    if any(not o.tracking_number and o.status not in ("delivered", "cancelled") for o in orders):
        parts.append(
            "\nĐơn hàng đang được xử lý — em sẽ cập nhật mã vận đơn ngay khi "
            "hàng được bàn giao cho đơn vị vận chuyển. Bạn cần hỗ trợ thêm gì không ạ?"
        )

    return "\n".join(parts)
