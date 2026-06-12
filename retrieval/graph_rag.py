"""
Graph RAG module — augments vector search with entity-relationship traversal.

Product graph structure (thesis §2.3.2):
  Product → Category → Brand → Occasion → Price Range

Entity extraction identifies nodes relevant to the query; graph traversal
expands them to related entities, enriching the semantic context fed into
the hybrid search stage.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path

from core.logger import custom_logger

_GRAPH_PATH = Path(__file__).resolve().parent.parent / "resources" / "data" / "entity_graph.json"


def _load_entity_graph() -> dict[str, list[str]]:
    """
    @desc Đọc và nạp đồ thị thực thể từ file JSON vào bộ nhớ — trả về dict rỗng nếu file không tồn tại hoặc bị lỗi
    @return dict[str, list[str]]: Dictionary ánh xạ tên thực thể sang danh sách các thực thể liên quan
    """
    try:
        with open(_GRAPH_PATH, encoding="utf-8") as f:
            data: dict[str, list[str]] = json.load(f)
        custom_logger.info(f"[GraphRAG] Entity graph loaded | nodes={len(data)} | path={_GRAPH_PATH}")
        return data
    except FileNotFoundError:
        custom_logger.warning(f"[GraphRAG] entity_graph.json not found at {_GRAPH_PATH}, using empty graph")
        return {}
    except Exception as exc:
        custom_logger.error(f"[GraphRAG] Failed to load entity graph: {exc}", exc_info=True)
        return {}


ENTITY_GRAPH: dict[str, list[str]] = _load_entity_graph()


@dataclass
class GraphRAGContext:
    original_query: str
    expanded_entities: list[str] = field(default_factory=list)
    enriched_query: str = ""


def extract_entities(query: str) -> list[str]:
    """
    @desc Trích xuất các thực thể liên quan từ câu truy vấn bằng phương pháp so khớp từ khóa với đồ thị thực thể
    @params query (str): Câu truy vấn đầu vào của người dùng
    @return list[str]: Danh sách các thực thể tìm thấy trong câu truy vấn
    """
    query_lower = query.lower()
    found: list[str] = []
    for entity in ENTITY_GRAPH:
        if entity in query_lower:
            found.append(entity)
    return found


def traverse_graph(entities: list[str], hops: int = 1) -> list[str]:
    """
    @desc Duyệt đồ thị theo chiều rộng (BFS) để mở rộng tập thực thể ban đầu sang các thực thể lân cận trong phạm vi số bước nhảy cho trước
    @params entities (list[str]): Danh sách thực thể gốc cần mở rộng
    @params hops (int): Số bước nhảy tối đa trong đồ thị khi duyệt
    @return list[str]: Danh sách tất cả các thực thể sau khi mở rộng (bao gồm cả thực thể gốc)
    """
    visited: set[str] = set(entities)
    frontier = list(entities)

    for _ in range(hops):
        next_frontier: list[str] = []
        for entity in frontier:
            for neighbor in ENTITY_GRAPH.get(entity, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    next_frontier.append(neighbor)
        frontier = next_frontier

    return list(visited)


def build_graphrag_context(query: str) -> GraphRAGContext:
    """
    @desc Thực thi toàn bộ pipeline Graph RAG: trích xuất thực thể, duyệt đồ thị và làm giàu câu truy vấn với ngữ cảnh mở rộng
    @params query (str): Câu truy vấn gốc của người dùng
    @return GraphRAGContext: Đối tượng chứa câu truy vấn gốc, danh sách thực thể mở rộng và câu truy vấn đã được làm giàu
    """
    entities = extract_entities(query)
    all_entities = traverse_graph(entities, hops=1)

    enriched = query
    if all_entities:
        enriched = f"{query} ({', '.join(all_entities)})"

    return GraphRAGContext(
        original_query=query,
        expanded_entities=all_entities,
        enriched_query=enriched,
    )


def enrich_query(query: str) -> str:
    """
    @desc Hàm tiện ích bọc ngoài build_graphrag_context — chỉ trả về chuỗi câu truy vấn đã được làm giàu
    @params query (str): Câu truy vấn gốc của người dùng
    @return str: Câu truy vấn sau khi được làm giàu bằng các thực thể mở rộng từ đồ thị
    """
    return build_graphrag_context(query).enriched_query
