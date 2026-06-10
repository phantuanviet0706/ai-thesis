from langgraph.graph import END

from common.constants import MAX_ITERATIONS, VALID_NODES
from graph.state import ConversationState


def conditional_router(state: ConversationState) -> str:
    """
    Reads state after every Orchestrator execution to determine the next node.
    Guards against error states and infinite loops before trusting next_node.

    See thesis §3.3.2 — Listing: Implementation of the Conditional Router.
    """
    if state.get("error_state") is not None:
        return "error_handler"

    if state.get("iteration_count", 0) > MAX_ITERATIONS:
        return END

    route = state.get("next_node", "")
    return route if route in VALID_NODES else END
