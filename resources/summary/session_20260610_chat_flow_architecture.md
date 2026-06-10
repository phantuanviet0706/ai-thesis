# Session Context — Pancharm AI Thesis
**Date:** 2026-06-10  
**Topic:** Thiết kế & hoàn thiện luồng xử lý chat end-to-end (Multi-Agent System)  
**Working dir:** `D:\ext_project\ai-thesis`

---

## 1. Project Snapshot

| Item | Value |
|------|-------|
| App name | Pancharm AI Retail Consultant |
| Domain | Tư vấn trang sức phong thủy (tiếng Việt) |
| Architecture | 4-agent MAS trên LangGraph DCG |
| API framework | FastAPI 0.136.3 + Uvicorn |
| LLM primary | `claude-sonnet-4-6` (Orchestrator, Synth) |
| LLM fast | `claude-haiku-4-5-20251001` (KR, Psych) |
| Embeddings | OpenAI `text-embedding-3-small` (1536 dims) |
| Vector DB | ChromaDB (PersistentClient, 3 collections) |
| Session store | Redis (LangGraph checkpoint, TTL=3600s) |
| Relational DB | MySQL (SQLAlchemy 2.0, sync + pymysql) |
| Python version | 3.11+ (dùng `X | Y` union type syntax) |

---

## 2. Cấu trúc thư mục quan trọng

```
ai-thesis/
├── main.py                          # FastAPI app, lifespan pre-warm graph
├── database.py                      # SQLAlchemy engine + get_db() context manager ← THÊM session này
├── requirements.txt                 # UTF-16 LE (encoding đặc biệt, không edit thủ công)
│
├── api/
│   ├── api_router.py                # include chat_router tại prefix /v1
│   └── chat_router.py               # POST /chat (sync 30s), GET /chat/stream (SSE)
│
├── controller/
│   └── chat_controller.py           # handle_chat() + _persist_turn() ← SỬA session này
│
├── graph/
│   ├── graph.py                     # _build_graph(), compile_graph(), get_compiled_graph()
│   ├── state.py                     # ConversationState TypedDict + PsychState enum
│   └── router.py                    # conditional_router() — guard loops + route
│
├── agents/
│   ├── orchestrator.py              # CoT routing (Sonnet, temp=0.0, max_tokens=512)
│   ├── kr_agent.py                  # 3-stage retrieval (Haiku, temp=0.0, max_tokens=256)
│   ├── psych_agent.py               # Zero-shot psych classification (Haiku, temp=0.0)
│   └── synth_agent.py               # AIDA response gen (Sonnet, temp=0.7, max_tokens=1024) ← SỬA
│
├── retrieval/
│   ├── hybrid_search.py             # Dense(0.50)+BM25(0.30)+Meta(0.20) → MMR top-5
│   ├── chromadb_client.py           # 3 collections: overview/specs/reviews
│   ├── embeddings.py                # OpenAI embed_query(), embed_documents()
│   └── graph_rag.py                 # Entity graph traversal (in-memory ENTITY_GRAPH)
│
├── repositories/
│   ├── __init__.py                  ← THÊM session này
│   └── conversation_repository.py  ← THÊM session này
│
├── models/                          # SQLAlchemy ORM (16 models)
│   ├── base_model.py                # Base, TimestampMixin, SoftDeleteMixin, ActiveMixin
│   ├── conversation_session.py      # ConversationSessions table
│   ├── conversation_message.py      # ConversationMessages table
│   └── agent_performance_log.py     # AgentPerformanceLogs table
│
├── schemas/
│   ├── chat_schema.py               # ChatRequest, ChatResponse (Pydantic)
│   └── api_schema.py                # ApiResponse[T] generic wrapper
│
├── entity/
│   └── product_doc.py               # ProductDoc (retrieved product from ChromaDB)
│
├── common/
│   └── constants.py                 # MAX_ITERATIONS=8, weights, TTL, PSYCH_STATES
│
├── core/
│   ├── config.py                    # Settings (pydantic-settings, loads .env)
│   └── logger.py                    # custom_logger (rotating file, 30-day)
│
├── infrastructure/
│   └── redis_client.py              # redis_client (connection pool)
│
└── resources/
    ├── prompt/
    │   ├── orchestrator_agent.md    # Routing priority table + few-shot CoT
    │   ├── kr_agent.md              # Query expansion taxonomy + collection selection
    │   ├── psych_agent.md           # 5 psych states + linguistic markers
    │   └── synth_agent.md           # AIDA model + factual grounding constraints
    └── summary/
        └── session_20260610_chat_flow_architecture.md  ← file này
```

---

## 3. ConversationState — Schema trung tâm

```python
# graph/state.py
class ConversationState(TypedDict):
    messages:          Annotated[list[BaseMessage], add_messages]  # append reducer
    user_intent:       str                    # overwrite — Orchestrator output
    next_node:         str                    # overwrite — routing signal
    retrieved_products: list[ProductDoc]      # overwrite — KR Agent output
    retrieval_scores:  list[float]            # overwrite
    psych_state:       PsychState             # overwrite — Psych Agent output
    psych_confidence:  float                  # overwrite
    primary_concern:   Optional[str]          # overwrite
    consult_strategy:  str                    # overwrite
    session_metadata:  Annotated[dict, _merge_dicts]  # merge reducer
    final_response:    str                    # overwrite — Synth Agent output
    error_state:       Optional[str]          # overwrite — triggers error_handler
    iteration_count:   Annotated[int, operator.add]   # add reducer

class PsychState(str, Enum):
    CURIOUS = "CURIOUS"       # Khám phá
    INTERESTED = "INTERESTED" # Quan tâm
    HESITATION = "HESITATION" # Phân vân
    COMMITTED = "COMMITTED"   # Sẵn sàng mua
    OBJECTING = "OBJECTING"   # Phản bác
```

---

## 4. Topology đồ thị (LangGraph DCG)

```
START
  │
  ▼
[orchestrator] ──[conditional_router]──► [kr_agent] ──────────┐
      ▲                                                         │
      │                               ──► [psych_agent] ───────┤
      └─────────────────────────────────────────────────────────┘
                                      ──► [synth_agent] ──────► END
                                      ──► [error_handler] ───► END
                                      ──► END  (MAX_ITERATIONS > 8)
```

**Routing priority (orchestrator_agent.md):**
1. `error_state != None` → `error_handler` (guard trong router)
2. `iteration_count > 8` → `END` (guard trong router)
3. `retrieved_products` rỗng → `kr_agent`
4. `psych_state` chưa có → `psych_agent`
5. Câu hỏi sản phẩm mới (intent thay đổi) → `kr_agent`
6. Đủ context → `synth_agent`

---

## 5. Luồng xử lý end-to-end (hoàn chỉnh)

```
HTTP POST /api/v1/chat
  { session_id?, message, channel, user_id? }
           │
           ▼ Pydantic validation + CORS
           │ asyncio.wait_for(30s)
           ▼
  controller/chat_controller.py :: handle_chat()
    ├─ session_id = request.session_id OR uuid4()
    ├─ input_state = {
    │     messages: [HumanMessage(message)],   ← add_messages sẽ append vào history cũ
    │     session_metadata: {...},
    │     iteration_count: 0,                  ← reset mỗi turn
    │     retrieved_products: [],              ← xóa kết quả cũ
    │     final_response: "",
    │     error_state: None
    │  }
    └─ graph.ainvoke(input_state, config={thread_id: session_id})
           │
           ▼ Redis checkpoint LOAD (thread_id → state cũ nếu có)
           │ Merge input_state vào state đã load
           │
           ▼ START → orchestrator_node()
    ┌──────────────────────────────────────────────┐
    │  ORCHESTRATOR (claude-sonnet-4-6)            │
    │  Input: last_user_message + state_summary    │
    │  Output JSON: {next_node, user_intent}       │
    │  CoT: Intent → State eval → Gap → Route      │
    └────────────────┬─────────────────────────────┘
                     │ conditional_router()
          ┌──────────┼──────────┐
          ▼          ▼          ▼
    [kr_agent]  [psych_agent]  [synth_agent]
          │          │
          │  KR (claude-haiku-4-5):
          │  Stage1: Graph RAG entity expand
          │          + LLM synonym expansion
          │          → final_query
          │  Stage2: embed_query (OpenAI 1536d)
          │          ChromaDB query × 3 collections
          │          Dense(cos) + BM25 + Meta
          │          composite = 0.50d + 0.30s + 0.20m
          │  Stage3: MMR(λ=0.7) → top-5 ProductDoc
          │  Return: {retrieved_products, next_node="orchestrator"}
          │
          │  PSYCH (claude-haiku-4-5):
          │  Input: conversation history (10 turns)
          │  Zero-shot → {psych_state, confidence,
          │               primary_concern, consult_strategy}
          │  Return: {psych_*, next_node="orchestrator"}
          │
          └──────────────► loop về orchestrator
                           khi đủ context → synth_agent
                                    │
                    SYNTH (claude-sonnet-4-6, temp=0.7):
                    Input: last_msg + user_intent
                           + psych_label + strategy
                           + 5 sản phẩm (formatted)
                    Output: AIDA-structured response
                    Return: {
                      messages: [AIMessage(response)],  ← GHI VÀO HISTORY
                      final_response: response
                    }
                           │
                           ▼ END
           Redis checkpoint SAVE
           (messages bao gồm HumanMsg + AIMsg của turn này)
                           │
                           ▼ asyncio.create_task() — fire & forget
           MySQL persist (không block response):
             UPSERT ConversationSessions (thread_id, psych_state, total_turns+1)
             INSERT ConversationMessages role=user
             INSERT ConversationMessages role=assistant
                           │
                           ▼
  ChatResponse {
    session_id, response, psych_state, psych_confidence,
    consult_strategy, retrieved_product_count, latency_ms, iteration_count
  }
  → ApiResponse[ChatResponse] { code:200, message:"Success", result:... }
```

---

## 6. Những thay đổi thực hiện trong session này

### Bug fixes (critical)

| File | Vấn đề | Fix |
|------|---------|-----|
| `agents/synth_agent.py:103` | `final_response` chỉ ghi vào field riêng, không ghi vào `state.messages` → multi-turn context bị mất | Thêm `"messages": [AIMessage(content=response.content)]` vào return dict |
| `graph/graph.py:36` | `_error_handler_node` không ghi AIMessage vào messages | Thêm `"messages": [AIMessage(content=fallback)]` |

**Hậu quả nếu không fix:** Psych Agent nhìn conversation history chỉ toàn HumanMessage, không thấy AI đã trả lời gì → phân tích tâm lý sai; Orchestrator đánh giá state sai → loop vô tận hoặc routing nhầm.

### Files mới tạo

| File | Mục đích |
|------|---------|
| `database.py` | SQLAlchemy engine (`mysql+pymysql`), `SessionLocal`, `get_db()` context manager (auto commit/rollback/close) |
| `repositories/__init__.py` | Package marker |
| `repositories/conversation_repository.py` | `ConversationRepository`: `upsert_session()`, `log_message()`, `update_session_after_turn()` |

### Files đã sửa

| File | Thay đổi |
|------|---------|
| `controller/chat_controller.py` | Thêm `_persist_turn_async()` + `_persist_turn()`: sau mỗi turn ghi session + messages vào MySQL qua `asyncio.create_task()` (fire-and-forget, lỗi DB không làm hỏng chat) |

---

## 7. Dependency còn thiếu cần install

```bash
pip install pymysql
```

`requirements.txt` của project có encoding đặc biệt (UTF-16 LE), không edit thủ công — dùng `pip install` trực tiếp rồi `pip freeze > requirements.txt`.

---

## 8. Database schema liên quan (MySQL)

```sql
-- ConversationSessions
thread_id         VARCHAR(36)  UNIQUE  -- = LangGraph thread_id = session_id từ client
user_id           BIGINT FK Users
channel           VARCHAR(50)          -- web|mobile|facebook|zalo|tiktok
status            VARCHAR(50)          -- active|completed|abandoned|error
final_psych_state VARCHAR(50)          -- CURIOUS|INTERESTED|HESITATION|COMMITTED|OBJECTING
total_turns       INT
iteration_count   INT
conversion_outcome VARCHAR(50)         -- no_intent|expressed_interest|added_to_cart|purchased
started_at        DATETIME
last_active_at    DATETIME             -- update mỗi turn

-- ConversationMessages
session_id   BIGINT FK ConversationSessions
turn_number  INT
role         VARCHAR(50)              -- user | assistant
content      TEXT
agent_name   VARCHAR(50)              -- synth_agent (chỉ ghi khi role=assistant)
latency_ms   INT
```

---

## 9. ChromaDB — 3 collections

| Collection | Chunk size | Use case |
|------------|-----------|----------|
| `product_overview` | 256 tokens, 32 overlap | Câu hỏi chung, tìm kiếm theo danh mục |
| `product_specs` | 512 tokens, 64 overlap | Câu hỏi kỹ thuật, thông số chi tiết |
| `product_reviews` | 384 tokens, 48 overlap | Câu hỏi về trải nghiệm, độ tin cậy |

ProductDoc fields: `id, name, sku, short_description, description, category, brand, unit_price, sale_price, in_stock, attributes, collection_source, chunk_text, composite_score`

---

## 10. Hybrid Search — công thức

```
composite_score = 0.50 × dense_score   (cosine similarity, OpenAI embedding)
                + 0.30 × bm25_score    (BM25Okapi, normalized)
                + 0.20 × meta_score    (binary: 1.0 nếu all hard filters match)

MMR(doc_i) = 0.7 × relevance(doc_i, query) - 0.3 × max_sim(doc_i, selected)
→ top-5 diverse results
```

Constants ở `common/constants.py`: `LAMBDA_DENSE=0.50`, `LAMBDA_SPARSE=0.30`, `LAMBDA_META=0.20`, `MMR_LAMBDA=0.7`, `TOP_K_INITIAL=20`, `TOP_K_FINAL=5`

---

## 11. Config (`.env` / `core/config.py`)

```
ANTHROPIC_API_KEY=...
ANTHROPIC_MODEL_PRIMARY=claude-sonnet-4-6
ANTHROPIC_MODEL_FAST=claude-haiku-4-5-20251001
OPENAI_API_KEY=...
CHROMA_PATH=D:/ext_project/ai-thesis/chroma_db
DB_HOST=localhost  DB_PORT=3306  DB_USER=root  DB_PASSWORD=123456  DB_NAME=ai_chatbot
REDIS_HOST=localhost  REDIS_PORT=6379
```

---

## 12. Những gì còn chưa triển khai (backlog)

| Hạng mục | Độ ưu tiên | Ghi chú |
|----------|-----------|---------|
| ChromaDB data ingestion | HIGH | Collections hiện tại trống — cần script nạp dữ liệu sản phẩm từ MySQL vào ChromaDB |
| `services/` layer | MEDIUM | Directory trống, business logic tư vấn nâng cao có thể đặt ở đây |
| Rate limiting middleware | MEDIUM | Constant `RATE_LIMIT_RPM=100` đã có nhưng middleware chưa implement |
| SSE streaming thật sự | LOW | `chat_stream` hiện tại chỉ word-split response sau khi graph chạy xong, không phải true token streaming |
| `AgentPerformanceLogs` | LOW | Model đã có nhưng controller chưa ghi latency/token per agent |
| `PsychStateLogs` | LOW | Model đã có nhưng chưa được ghi |
| Auth middleware | MEDIUM | JWT config đã có nhưng endpoint chưa protect |

---

## 13. Lệnh chạy

```bash
# Install missing dep
pip install pymysql

# Run server
uvicorn main:app --host 0.0.0.0 --port 8088 --reload

# Test chat
curl -X POST http://localhost:8088/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Tôi muốn tìm nhẫn tặng sinh nhật cho vợ, khoảng 3 triệu", "channel": "web"}'
```

---

## 14. Điểm kiến trúc đặc biệt (cho thesis)

1. **Psych Agent là first-class agent** — không phải tool hay post-hoc, mà là node đầy đủ trong DCG, continuously shaping consultation strategy (contribution mới so với RAG thuần)
2. **Reducer-based state merge** — mỗi agent chỉ trả delta, LangGraph merge vào centralized state → agents độc lập, không coupling trực tiếp
3. **Dual-memory architecture** — Redis (short-term, 1h TTL) cho context window + MySQL (long-term, permanent) cho analytics và conversion tracking
4. **Fire-and-forget DB persistence** — DB write không block response latency, lỗi DB không làm down chat
5. **Zero-shot psych classification** — không cần annotated training data, critical cho Vietnamese context khan hiếm data
