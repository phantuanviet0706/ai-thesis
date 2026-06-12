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

    # Loop guard — incremented (+1) each Orchestrator cycle via add reducer
    iteration_count: Annotated[int, operator.add]
