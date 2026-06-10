"""
Graph RAG module — augments vector search with entity-relationship traversal.

Product graph structure (thesis §2.3.2):
  Product → Category → Brand → Occasion → Price Range

Entity extraction identifies nodes relevant to the query; graph traversal
expands them to related entities, enriching the semantic context fed into
the hybrid search stage.
"""

from dataclasses import dataclass, field

# ─── In-memory entity graph ───────────────────────────────────────────────────
# In production this would be loaded from the database or a graph store.
# Format: entity_name → list[related_entity_names]

ENTITY_GRAPH: dict[str, list[str]] = {
    # Occasions
    "sinh nhật": ["nhẫn phong thủy", "vòng tay bạc", "dây chuyền vàng", "quà tặng cao cấp"],
    "cưới": ["nhẫn cưới", "nhẫn đính hôn", "bộ trang sức cưới", "vàng 18k"],
    "valentine": ["nhẫn tình yêu", "vòng tay đôi", "dây chuyền trái tim"],
    "tết": ["nhẫn vàng", "trang sức vàng", "quà tặng may mắn", "phong thủy"],
    "khai trương": ["la bàn phong thủy", "trang sức phong thủy", "mệnh hỏa", "mệnh thổ"],
    # Categories → related products
    "nhẫn": ["nhẫn phong thủy", "nhẫn cưới", "nhẫn đính hôn", "nhẫn vàng", "nhẫn bạc"],
    "vòng tay": ["vòng tay bạc", "vòng tay vàng", "vòng tay phong thủy", "lắc tay"],
    "dây chuyền": ["dây chuyền vàng", "dây chuyền bạc", "mặt dây chuyền"],
    "bông tai": ["hoa tai vàng", "bông tai bạc", "khuyên tai"],
    # Feng shui elements
    "mệnh kim": ["bạc", "trắng", "vàng trắng"],
    "mệnh mộc": ["xanh lá", "gỗ", "ngọc bích"],
    "mệnh thủy": ["đen", "xanh dương", "bạc"],
    "mệnh hỏa": ["đỏ", "vàng", "ruby", "đá đỏ"],
    "mệnh thổ": ["vàng", "nâu", "đá vàng"],
    # Price ranges
    "giá rẻ": ["dưới 1 triệu", "bình dân", "học sinh sinh viên"],
    "tầm trung": ["1-5 triệu", "nhân viên văn phòng"],
    "cao cấp": ["trên 10 triệu", "luxury", "quà tặng vip"],
}


@dataclass
class GraphRAGContext:
    original_query: str
    expanded_entities: list[str] = field(default_factory=list)
    enriched_query: str = ""


def extract_entities(query: str) -> list[str]:
    """Keyword-based entity extraction from query (production would use NER)."""
    query_lower = query.lower()
    found: list[str] = []
    for entity in ENTITY_GRAPH:
        if entity in query_lower:
            found.append(entity)
    return found


def traverse_graph(entities: list[str], hops: int = 1) -> list[str]:
    """BFS traversal — expand each entity to its neighbors up to `hops` levels."""
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
    Full Graph RAG pipeline:
    1. Extract entities from query
    2. Traverse entity graph to find related concepts
    3. Enrich the query string with expanded context
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
    """Convenience wrapper — returns only the enriched query string."""
    return build_graphrag_context(query).enriched_query
