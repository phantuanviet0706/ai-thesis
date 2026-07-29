import operator
from enum import Enum
from typing import Annotated, Any, Optional

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from entity.product_doc import ProductDoc


class PsychState(str, Enum):
    CURIOUS = "CURIOUS"
    INTERESTED = "INTERESTED"
    HESITATION = "HESITATION"
    COMMITTED = "COMMITTED"
    OBJECTING = "OBJECTING"


def _merge_dicts(current: dict, update: dict) -> dict:
    """
    @desc Gộp hai dict lại với nhau, các key trùng sẽ được ghi đè bởi giá trị từ dict mới
    @params current (dict): Dict hiện tại trong trạng thái hội thoại
    @params update (dict): Dict mới chứa các giá trị cần cập nhật hoặc thêm vào
    @return dict: Dict kết quả sau khi gộp, dùng làm reducer cho trường session_metadata
    """
    return {**current, **update}


_CARRY_FORWARD_KEYS = (
    "customer_name", "customer_phone", "customer_address",
    "zodiac_sign", "birth_year", "gender",
)


def _merge_extracted_info(current: Optional[dict], update: Optional[dict]) -> Optional[dict]:
    """
    @desc Reducer cho extracted_info — tích lũy preferences (mệnh, budget, material, style, occasion...)
    và các trường định danh (tên/SĐT/địa chỉ/mệnh/năm sinh/giới tính) qua nhiều lượt hội thoại thay vì
    ghi đè hoàn toàn, vì Extraction Agent chỉ trích xuất những gì khách nói RÕ Ở LƯỢT HIỆN TẠI — nếu ghi đè
    toàn bộ, thông tin đã biết từ lượt trước (vd mệnh Kim nói ở lượt 2) sẽ biến mất khỏi context của KR/Synth
    Agent ở lượt 5 dù khách chưa hề rút lại. order_intent/conversion_outcome/selected_product_ids vẫn ghi đè
    theo lượt hiện tại vì đó là tín hiệu chỉ có giá trị cho đúng lượt đang xử lý (business logic cần vậy).
    @params current (Optional[dict]): Giá trị extracted_info tích lũy tới trước lượt này
    @params update (Optional[dict]): Kết quả Extraction Agent trả về ở lượt hiện tại (có thể None nếu lỗi)
    @return Optional[dict]: extracted_info đã merge, ưu tiên giá trị mới nhưng giữ lại thông tin cũ khi mới = null
    """
    if update is None:
        return current
    if current is None:
        return update

    merged = {**current, **update}
    merged["preferences"] = {**(current.get("preferences") or {}), **(update.get("preferences") or {})}

    for key in _CARRY_FORWARD_KEYS:
        if update.get(key) is None and current.get(key) is not None:
            merged[key] = current[key]

    return merged


class ConversationState(TypedDict):
    """
    Centralized state shared across all agents in the LangGraph DCG.
    Each field has a reducer that governs how updates from node deltas are merged.
    See thesis Table 3.1 for full schema specification.
    """
    # Full conversation history — append reducer preserves chronological order
    messages: Annotated[list[BaseMessage], add_messages]

    # Orchestrator output — overwrite per turn
    user_intent: str

    # KR Agent output — overwrite with fresh retrieval results per turn
    retrieved_products: list[ProductDoc]
    retrieval_scores: list[float]

    # True khi KR Agent không tìm được sản phẩm nào trong đúng ngân sách khách nêu và đã tự động
    # bỏ filter giá để tìm sản phẩm đúng mệnh/danh mục gần nhất (xem agents/kr_agent.py) — báo cho
    # Synth Agent biết giá sản phẩm trong retrieved_products đã VƯỢT ngân sách khách nêu, tránh
    # vòng lặp hỏi nới giá nhiều lượt liên tiếp.
    budget_relaxed: bool

    # Snapshot of retrieved_products từ LƯỢT TRƯỚC — ghi bởi Extraction Agent (xem
    # agents/extraction_agent.py) SAU KHI Synth/Extraction Agent của lượt hiện tại đã đọc
    # xong giá trị cũ. Không được ghi bởi kr_agent vì retrieved_products đã bị reset về []
    # trong ChatService._build_input_state trước khi graph chạy mỗi lượt — nếu không có field
    # riêng này, tham chiếu kiểu "mẫu còn lại"/"cái kia" ở lượt sau sẽ mất hoàn toàn ngữ cảnh
    # sản phẩm đã gợi ý trước đó.
    previous_turn_products: list[ProductDoc]

    # Psych Agent output — overwrite with latest classification
    psych_state: PsychState
    psych_confidence: float
    primary_concern: Optional[str]
    consult_strategy: str

    # Cross-session metadata — merge (dict update) to accumulate fields
    session_metadata: Annotated[dict[str, Any], _merge_dicts]

    # Synth Agent output — final response for this turn
    final_response: str

    # Routing signal read by conditional_router after Orchestrator runs
    next_node: str

    # Error state — triggers error_handler branch if non-None
    error_state: Optional[str]

    # Loop guard — overwrite each cycle; Orchestrator returns current+1 explicitly
    iteration_count: int

    # Extraction Agent output — structured info extracted from conversation.
    # Merged (not overwritten) across turns via _merge_extracted_info, xem docstring của
    # hàm đó để biết field nào tích lũy và field nào ghi đè theo lượt.
    extracted_info: Annotated[Optional[dict], _merge_extracted_info]
