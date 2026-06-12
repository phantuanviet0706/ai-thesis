# Kiến Trúc Tổng Quan — Pancharm AI Retail Consultant
**Cập nhật:** 2026-06-12 (rev 2 — rate limit, auth, SSE streaming, Graph RAG từ JSON)  
**Working dir:** `D:\ext_project\ai-thesis`

---

## 1. Tổng Quan Dự Án

**Pancharm AI Retail Consultant** là một hệ thống Multi-Agent System (MAS) tư vấn bán lẻ trang sức phong thủy bằng tiếng Việt, xây dựng trên nền tảng LangGraph DCG (Directed Cyclic Graph). Hệ thống kết hợp 4 agent chuyên biệt, retrieval pipeline 3 tầng, và bộ nhớ kép Redis + PostgreSQL để cung cấp trải nghiệm tư vấn cá nhân hóa theo tâm lý khách hàng.

| Thuộc tính | Giá trị |
|-----------|---------|
| Tên ứng dụng | Pancharm AI Retail Consultant |
| Domain | Tư vấn trang sức phong thủy (tiếng Việt) |
| Kiến trúc core | 4-agent MAS trên LangGraph DCG |
| API framework | FastAPI + Uvicorn |
| LLM chính | `claude-sonnet-4-6` (Orchestrator, Synth Agent) |
| LLM nhanh | `claude-haiku-4-5-20251001` (KR Agent, Psych Agent) |
| Embedding model | OpenAI `text-embedding-3-small` (1536 dims) |
| Vector DB | ChromaDB PersistentClient (3 collections, HNSW cosine) |
| Session store | Redis (LangGraph checkpoint, TTL = 3600s) |
| Relational DB | PostgreSQL (SQLAlchemy 2.x + psycopg2) |
| Auth | JWT Bearer — HS512 (`python-jose`) |
| Rate limit | 100 RPM per IP (sliding window, in-memory) |
| Python | 3.11+ |

---

## 2. Kiến Trúc Phân Tầng

```
┌─────────────────────────────────────────────────────────────┐
│  CLIENT  (Web / Mobile / Facebook / Zalo / TikTok)          │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP REST / SSE
┌──────────────────────────▼──────────────────────────────────┐
│  MIDDLEWARE STACK  (Starlette, outermost → innermost)        │
│  1. RateLimitMiddleware  — 100 RPM/IP, sliding window       │
│  2. CORSMiddleware       — approved origins only            │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│  LAYER 1 — API  (FastAPI + @cbv)                            │
│  api/v1/endpoints/base/chat_controller.py                   │
│  POST /chat  [require_auth]   GET /chat/stream [opt_auth]   │
│  api/deps.py — require_auth / optional_auth (JWT Bearer)    │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│  LAYER 2 — SERVICE                                          │
│  services/chat_service.py                                   │
│  • handle_chat()    → graph.ainvoke (POST /chat)            │
│  • stream_chat()    → graph.astream_events (SSE /stream)    │
│  • _persist_turn_async() fire-and-forget                    │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│  LAYER 3 — MAS CORE  (LangGraph DCG)                        │
│  graph/graph.py + graph/router.py                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐  │
│  │Orchestrat│  │ KR Agent │  │  Psych   │  │   Synth    │  │
│  │   or     │  │          │  │  Agent   │  │ Agent async│  │
│  └──────────┘  └──────────┘  └──────────┘  └────────────┘  │
└──────────┬─────────────────┬───────────────────────────────-┘
           │                 │
┌──────────▼──────┐  ┌───────▼─────────────────────────────┐
│  LAYER 4a       │  │  LAYER 4b — RETRIEVAL               │
│  REPOSITORY     │  │  retrieval/hybrid_search.py         │
│  PostgreSQL     │  │  retrieval/graph_rag.py (JSON-based)│
│  (async bg)     │  │  retrieval/embeddings.py            │
└─────────────────┘  └─────────────────────────────────────┘
           │                         │
┌──────────▼──────────────┐  ┌───────▼─────────────────────┐
│  PostgreSQL             │  │  ChromaDB (3 collections)   │
│  (24 ORM entities)      │  │  + Redis  (LG checkpoint)   │
└─────────────────────────┘  └─────────────────────────────┘
```

---

## 3. Cấu Trúc Thư Mục

```
ai-thesis/
│
├── main.py                          # FastAPI app + RateLimitMiddleware + lifespan pre-warm
├── database.sql                     # PostgreSQL schema (6 domains, 18 tables)
│
├── api/
│   ├── api_router.py                # Root router, register tất cả sub-routers
│   ├── deps.py                      # require_auth / optional_auth (JWT Bearer FastAPI deps)
│   ├── chat_router.py               # [deprecated] — đã chuyển sang v1/endpoints
│   └── v1/endpoints/base/
│       ├── chat_controller.py       # @cbv: POST /chat [require_auth] + GET /stream [opt_auth]
│       └── sample_controller.py    # Mẫu CBV pattern
│
├── services/
│   ├── base_service.py              # BaseService[T, R] — get_all, get_by_id, delete
│   ├── chat_service.py              # handle_chat (ainvoke) + stream_chat (astream_events)
│   └── sample_service.py           # SampleService (mẫu)
│
├── controller/
│   └── chat_controller.py          # [deprecated] — logic đã chuyển sang services/
│
├── graph/
│   ├── graph.py                    # _build_graph(), compile_graph(), get_compiled_graph()
│   ├── router.py                   # conditional_router() — guard + routing
│   └── state.py                    # ConversationState TypedDict + PsychState enum
│
├── agents/
│   ├── orchestrator.py             # CoT routing (Sonnet, temp=0.0, max_tokens=512)
│   ├── kr_agent.py                 # 3-stage retrieval (Haiku, temp=0.0, max_tokens=256)
│   ├── psych_agent.py              # Zero-shot psych classification (Haiku, temp=0.0)
│   └── synth_agent.py              # async AIDA gen — llm.astream() → true SSE tokens
│
├── retrieval/
│   ├── hybrid_search.py            # Dense(0.50)+BM25(0.30)+Meta(0.20) → MMR top-5
│   ├── chromadb_client.py          # Facade → database/vector_db_manager
│   ├── embeddings.py               # OpenAI embed_query(), embed_documents()
│   └── graph_rag.py                # Load ENTITY_GRAPH từ resources/data/entity_graph.json
│
├── database/
│   ├── __init__.py                 # get_db() context manager → PostgreSQL
│   ├── database.py                 # DBManager factory + DatabaseSettings base class
│   ├── postgres_manager.py         # PostgresConfig + PostgresManager (primary DB)
│   ├── mysql_manager.py            # MySQLConfig + MySQLManager (optional)
│   └── vector_db_manager.py        # VectorDBManager singleton (ChromaDB, 3 collections)
│
├── middleware/
│   ├── __init__.py
│   └── rate_limit_middleware.py    # Sliding-window 100 RPM/IP (BaseHTTPMiddleware)
│
├── core/
│   ├── config.py                   # Settings (pydantic-settings, load .env)
│   ├── logger.py                   # custom_logger (rotating file, 30-day, UTF-8)
│   └── security.py                 # create_access_token, create_refresh_token, decode_token
│
├── entity/                         # SQLAlchemy ORM — 24 models, 6 domains
│   ├── base_model.py               # Base, TimestampMixin, SoftDeleteMixin, ActiveMixin
│   ├── __init__.py                 # Export tất cả 24 entities
│   │
│   │── [1] Core Product Domain
│   ├── brand.py  tag.py  category.py  product.py  product_image.py  product_tag.py
│   │── [2] User Domain
│   ├── user.py  user_profile.py  user_address.py
│   │── [3] Commerce Domain
│   ├── cart.py  cart_item.py  order.py  order_item.py  payment.py
│   │── [4] Content Domain
│   ├── product_review.py
│   │── [5] AI / Consultation Domain
│   ├── conversation_session.py  conversation_message.py
│   ├── psych_state_log.py  agent_performance_log.py
│   │── [6] Platform Domain
│   └── api_key.py  system_config.py  audit_log.py
│
├── repositories/
│   ├── base_repository.py          # BaseRepository[T] — CRUD generic
│   ├── conversation_repository.py  # upsert_session, log_message, update_session_after_turn
│   └── sample_repository.py        # (mẫu)
│
├── schemas/
│   ├── api_schema.py               # ApiResponse[T] generic wrapper
│   ├── base_schema.py              # BaseSchema, BaseListSchema (pagination + date filter)
│   ├── chat_schema.py              # ChatRequest, ChatResponse
│   └── sample_schema.py            # (mẫu)
│
├── infrastructure/
│   └── redis_client.py             # redis_client (connection pool, max_connections=10)
│
├── models/                         # LLM provider abstraction (legacy/experimental)
│   ├── base_llm_provider.py  model_factory.py  open_ai_provider.py
│   ├── huggingface_provider.py  huggingface_local_provider.py  ollama_provider.py
│
├── common/
│   ├── constants.py                # Hyperparameters, collection names, TTL, RATE_LIMIT_RPM
│   └── model_type.py               # ModelType enum
│
├── constants/
│   └── error_code.py               # ErrorCode enum (code, message, http_status)
│
├── utils/
│   └── helper.py                   # read_file_contents() — đọc prompt .md files
│
├── exceptions/
│   ├── app_exception.py            # AppException(ErrorCode)
│   └── global_exception_handler.py # FastAPI exception handlers
│
└── resources/
    ├── data/
    │   └── entity_graph.json       # Entity graph data (17 nodes, JSON-editable)
    ├── prompt/
    │   ├── orchestrator_agent.md  kr_agent.md  psych_agent.md  synth_agent.md
    └── summary/
        └── kien_truc_tong_quan.md  # This file
```

---

## 4. Multi-Agent System — 4 Agents

### 4.1 Topology LangGraph DCG

```
START
  │
  ▼
┌─────────────────────────────────────────────┐
│           ORCHESTRATOR                      │
│  Model: claude-sonnet-4-6                   │
│  temp=0.0 | max_tokens=512                  │
│  Input:  last_user_msg + state_summary      │
│  Output: {next_node, user_intent}           │
└───────────────┬─────────────────────────────┘
                │ conditional_router()
    ┌───────────┼───────────┬────────────────┐
    ▼           ▼           ▼                ▼
[kr_agent] [psych_agent] [synth_agent] [error_handler]
    │           │           │                │
    └──── back ─┘           ▼                ▼
      to orchestrator      END              END
```

**Luật routing (conditional_router):**

| Ưu tiên | Điều kiện | → Node |
|---------|-----------|--------|
| 0 | `error_state != None` | `error_handler` |
| 1 | `iteration_count > MAX_ITERATIONS (8)` | `END` |
| 2 | `next_node` không hợp lệ | `END` |
| 3 | `next_node` = giá trị hợp lệ | node tương ứng |

**VALID_NODES:** `{kr_agent, psych_agent, synth_agent, error_handler}`

---

### 4.2 Orchestrator Agent

**File:** `agents/orchestrator.py`  
**Model:** `claude-sonnet-4-6` | temp=0.0 | max_tokens=512

**Nhiệm vụ:** Trung tâm nhận thức — phân tích intent, đánh giá state, ra quyết định routing.

**Output JSON:**
```json
{
  "next_node": "kr_agent|psych_agent|synth_agent",
  "user_intent": "mô tả ý định người dùng"
}
```

**Fallback khi JSON parse lỗi:**  
`kr_agent` (nếu chưa có products) → `psych_agent` (nếu chưa có psych) → `synth_agent`

---

### 4.3 KR Agent (Knowledge Retrieval)

**File:** `agents/kr_agent.py`  
**Model:** `claude-haiku-4-5-20251001` | temp=0.0 | max_tokens=256

**3 giai đoạn:**

```
Stage 1 — Query Expansion
  ├── Graph RAG: load từ entity_graph.json → traverse_graph(1 hop)
  └── LLM expansion: {enriched_query, metadata_filters}

Stage 2 — Hybrid Search (qua 3 ChromaDB collections)
  Dense:  cosine similarity (OpenAI 1536d)   × 0.50
  Sparse: BM25Okapi normalized               × 0.30
  Meta:   binary filter match                × 0.20

Stage 3 — MMR Re-ranking (λ=0.7)
  TOP_K_INITIAL=20 candidates → TOP_K_FINAL=5 diverse results
```

**Output:** `{retrieved_products: [ProductDoc×5], retrieval_scores, next_node: "orchestrator"}`

---

### 4.4 Psych Agent (Psychology Analysis)

**File:** `agents/psych_agent.py`  
**Model:** `claude-haiku-4-5-20251001` | temp=0.0 | max_tokens=256  
**Đặc điểm:** Zero-shot classification — không cần annotated training data

| State | Tiếng Việt | Dấu hiệu ngôn ngữ |
|-------|-----------|-------------------|
| `CURIOUS` | Khám phá | Câu hỏi mở, "tìm hiểu", "muốn biết" |
| `INTERESTED` | Quan tâm | Hỏi chi tiết sản phẩm cụ thể |
| `HESITATION` | Phân vân | "suy nghĩ", "có lẽ", "hay là" |
| `COMMITTED` | Sẵn sàng mua | "đặt ngay", "mua", hỏi thanh toán |
| `OBJECTING` | Phản bác | Nghi ngờ chất lượng/giá |

**Fallback khi parse lỗi:** `CURIOUS | 0.5 | None | "Tiếp tục tư vấn chung"`

---

### 4.5 Synth Agent (Synthesis)

**File:** `agents/synth_agent.py`  
**Model:** `claude-sonnet-4-6` | temp=0.7 | max_tokens=1024  
**Kiểu hàm:** `async def synth_agent_node` — dùng `llm.astream()` thay cho `llm.invoke()`

**Tại sao async + astream:**  
`graph.astream_events(version="v2")` chỉ emit `on_chat_model_stream` events khi node gọi `llm.astream()`. Thay đổi này cho phép SSE endpoint push token ngay khi Anthropic generate, không cần chờ toàn bộ response.

**Ràng buộc cứng:**
1. **Factual Grounding** — chỉ dùng thông tin từ KR Agent, zero hallucination
2. **Strategy Alignment** — cấu trúc response theo `consult_strategy` từ Psych Agent
3. **Natural Tone** — tiếng Việt thân thiện, bản địa hóa văn hóa

**Cấu trúc AIDA:** Attention → Interest → Desire → Action (CTA hiệu chỉnh theo psych_state)

**Output:** `{messages: [AIMessage], final_response, error_state: None}`

---

## 5. ConversationState — Schema Trung Tâm

```python
class ConversationState(TypedDict):
    messages:          Annotated[list[BaseMessage], add_messages]  # reducer: append
    user_intent:       str
    next_node:         str
    retrieved_products: list[ProductDoc]
    retrieval_scores:  list[float]
    psych_state:       PsychState
    psych_confidence:  float
    primary_concern:   Optional[str]
    consult_strategy:  str
    session_metadata:  Annotated[dict, _merge_dicts]               # reducer: merge
    final_response:    str
    error_state:       Optional[str]
    iteration_count:   Annotated[int, operator.add]                # reducer: accumulate
```

**Reducer pattern:** Mỗi agent chỉ trả `delta dict` — LangGraph merge vào centralized state theo reducer. Agents hoàn toàn decoupled.

---

## 6. Retrieval Pipeline Chi Tiết

### 6.1 Graph RAG — Stage 1

**File:** `retrieval/graph_rag.py`  
**Data:** `resources/data/entity_graph.json` — JSON file có thể chỉnh sửa không cần deploy lại code

```
startup:
  _load_entity_graph() đọc entity_graph.json
  → ENTITY_GRAPH: dict[str, list[str]]  (17 nodes hiện tại)
  → [GraphRAG] Entity graph loaded | nodes=17

per-query:
  extract_entities(query) → keyword matching
  traverse_graph(entities, hops=1) → BFS expansion
  enriched_query = f"{query} ({expanded_entities})"
```

**Thêm entity mới:** chỉ cần sửa `resources/data/entity_graph.json`, không cần thay đổi code.

**Entity categories:** occasions (sinh nhật, cưới, tết...), product categories (nhẫn, vòng tay...), feng-shui elements (mệnh kim/mộc/thủy/hỏa/thổ), price ranges.

### 6.2 Hybrid Search — Stage 2 & 3

**File:** `retrieval/hybrid_search.py`

```
enriched_query → embed_query() → 1536d vector
  ├── product_overview  (256 tok, 32 overlap) ─┐
  ├── product_specs     (512 tok, 64 overlap) ──┼─ top-20 each
  └── product_reviews   (384 tok, 48 overlap) ─┘
       │
       ▼ composite_score = 0.50×dense + 0.30×BM25 + 0.20×meta
       ▼ MMR(λ=0.7): top-20 → top-5 diverse results
```

### 6.3 ProductDoc Schema

```python
class ProductDoc(BaseModel):
    id, name, sku, short_description, description
    category, brand, unit_price, sale_price, in_stock
    attributes: dict           # material, size, feng-shui props
    collection_source: str     # "product_overview"|"product_specs"|"product_reviews"
    chunk_text: str            # raw text chunk retrieved
    composite_score: float     # final hybrid score
```

---

## 7. Database Layer

### 7.1 PostgreSQL (Primary Relational DB)

**Kết nối:** `database/__init__.py` — `get_db()` context manager — `postgresql+psycopg2`  
**Pool:** `pool_size=10`, `max_overflow=20`, `pool_pre_ping=True`

**24 entities / 6 domains:**

```
[1] Core Product   — Brand, Tag, Category, Product, ProductImage, ProductTag
[2] User           — User, UserProfile, UserAddress
[3] Commerce       — Cart, CartItem, Order, OrderItem, Payment
[4] Content        — ProductReview
[5] AI/Consult     — ConversationSession, ConversationMessage,
                     PsychStateLog, AgentPerformanceLog
[6] Platform       — APIKey, SystemConfig, AuditLog
```

**ORM Mixins:**

| Mixin | Columns |
|-------|---------|
| `TimestampMixin` | `created_at DateTime`, `updated_at DateTime` (auto onupdate) |
| `SoftDeleteMixin` | `deleted_at DateTime` nullable + `is_deleted` property |
| `ActiveMixin` | `is_active SmallInteger` (0/1) |

### 7.2 ChromaDB (Vector DB)

**Kết nối:** `database/vector_db_manager.py` — `VectorDBManager` singleton  
**Index:** HNSW cosine — `{hnsw:space: cosine, hnsw:M: 16, hnsw:ef_construction: 200}`

| Collection | Chunk | Overlap | Mục đích |
|-----------|-------|---------|---------|
| `product_overview` | 256 tokens | 32 | USP — truy vấn chung |
| `product_specs` | 512 tokens | 64 | Technical specs |
| `product_reviews` | 384 tokens | 48 | Reviews, social proof |

### 7.3 Redis (Session Store / Checkpoint)

```
LangGraph RedisSaver:
  key pattern: {thread_id}:{checkpoint_id}
  TTL: 3600 giây (SESSION_TTL)
  Lợi ích: khôi phục ConversationState từ request trước
```

**Dual-memory:**

```
Redis (short-term, 1h)       PostgreSQL (long-term, permanent)
├── ConversationState        ├── ConversationSession
├── messages history         ├── ConversationMessage (full log)
├── psych_state              ├── PsychStateLog
└── retrieved_products       └── AgentPerformanceLog
```

---

## 8. Middleware & Security

### 8.1 Rate Limiting

**File:** `middleware/rate_limit_middleware.py`  
**Đăng ký:** `app.add_middleware(RateLimitMiddleware)` trong `main.py`

```
Mỗi request:
  client_ip = request.client.host
  Evict timestamps < (now - 60s)
  IF len(timestamps) >= 100 → HTTP 429 + Retry-After header
  ELSE timestamps.append(now) → proceed

Skip paths: /health, /docs, /openapi, /redoc, /favicon
Log: [RateLimit] 429 | ip=... | count=.../100 | retry_after=...s
```

**Scale note:** Store hiện tại là in-memory `defaultdict(list)` per process. Multi-instance deployment cần thay bằng Redis ZSET.

### 8.2 JWT Authentication

**File:** `core/security.py`

```python
create_access_token(subject, extra?)   → JWT, exp = now + 120 min
create_refresh_token(subject)          → JWT, exp = now + 30 min
decode_token(token)                    → payload dict | raise JWTError
```
Algorithm: HS512 | Secret: `settings.SECRET_KEY` | Library: `python-jose`

**File:** `api/deps.py` — FastAPI dependencies

```python
require_auth(credentials)   → payload dict   # raise 401 nếu thiếu/sai
optional_auth(credentials)  → dict | None    # guest-friendly (không raise)
```

**Áp dụng lên endpoints:**

| Endpoint | Auth | Lý do |
|----------|------|-------|
| `POST /api/v1/chat` | `require_auth` | API endpoint, phải có token |
| `GET /api/v1/chat/stream` | `optional_auth` | SSE, cần cho browser embed trực tiếp |

---

## 9. Layered Architecture — Request Flow

### 9.1 POST /chat — Synchronous Flow

```
HTTP POST /api/v1/chat
  Header: Authorization: Bearer <jwt>
  Body: { session_id?, message, channel, user_id? }
  │
  ▼ RateLimitMiddleware — 100 RPM/IP
  ▼ require_auth — decode JWT, extract sub
  ▼ ChatController.chat() — asyncio.wait_for(30s)
  │
  ▼ ChatService.handle_chat()
    ├── session_id = request.session_id OR uuid4()
    ├── _build_input_state() → input_state dict
    ▼ graph.ainvoke(input_state, config={thread_id})
        ├── Redis LOAD checkpoint
        ├── orchestrator_node() → conditional_router() → kr_agent
        ├── kr_agent_node()     → conditional_router() → psych_agent
        ├── psych_agent_node()  → conditional_router() → synth_agent
        └── synth_agent_node() [async, astream internally] → END
        └── Redis SAVE checkpoint
    ├── asyncio.create_task(_persist_turn_async(...))  ← fire & forget
    └── return ChatResponse
  │
  ▼ ApiResponse[ChatResponse] {code: 200, result: {...}}
```

### 9.2 GET /chat/stream — True Token Streaming Flow

```
GET /api/v1/chat/stream?message=...&session_id=...&channel=...
  Header: Authorization: Bearer <jwt>  (optional)
  │
  ▼ RateLimitMiddleware
  ▼ optional_auth — decode JWT if present (None = guest)
  ▼ ChatController.chat_stream()
  │
  ▼ ChatService.stream_chat()
    ├── session_id = request.session_id OR uuid4()
    ├── _build_input_state() → input_state dict
    ▼ graph.astream_events(input_state, config, version="v2")
        │
        │  Event loop (LangGraph emits events per node + per LLM call):
        │
        ├── [event: on_chat_model_stream, node: synth_agent]
        │    chunk = event["data"]["chunk"]
        │    yield {"token": chunk.content, "done": False}
        │    → SSE: data: {"token": "Xin", "done": false}
        │    → SSE: data: {"token": " chào", "done": false}
        │    → ... (realtime, ~20-50ms per token từ Anthropic)
        │
        ├── [event: on_chain_end, name: LangGraph]
        │    final_state = event["data"]["output"]
        │
        └── asyncio.create_task(_persist_turn_async(...))
    │
    ▼ yield {"done": True, "session_id": ..., "psych_state": ...,
             "psych_confidence": ..., "latency_ms": ..., "iteration_count": ...}
    │
  ▼ SSE final event: data: {"done": true, ...}
  Media-type: text/event-stream
  Headers: Cache-Control: no-cache, X-Accel-Buffering: no
```

**So sánh trước/sau:**

| | Trước | Sau |
|--|-------|-----|
| Khi nào bắt đầu stream | Sau khi graph hoàn thành | Ngay khi Synth Agent generate token đầu tiên |
| Cơ chế | `word.split()` + `asyncio.sleep(0.01)` | `astream_events` → `on_chat_model_stream` |
| Latency to first byte | ~toàn bộ graph time | Orchestrator + KR + Psych time |
| Token source | Xử lý local | Anthropic API realtime |

### 9.3 Error Handling Flow

```
Bất kỳ agent nào raise Exception
  └── agent trả: {error_state: "AgentName error: ...", next_node: "error_handler"}
        ▼ conditional_router() → error_handler
        ▼ _error_handler_node(): fallback response tiếng Việt + log ERROR
        ▼ END
```

---

## 10. Logging Architecture

**File:** `core/logger.py` — `custom_logger`  
**Format:** `%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s`  
**Handlers:** File (rotating daily, 30 ngày) + Console | **Encoding:** UTF-8

**Quy tắc level:**

| Level | Khi nào dùng |
|-------|-------------|
| `DEBUG` | Chi tiết nội bộ, per-item (per-collection hits, content_len) |
| `INFO` | Sự kiện bình thường (agent start/complete, routing, session) |
| `WARNING` | Lỗi có thể recover (rate limit, JSON fallback, DB persist fail) |
| `ERROR` | Lỗi nghiêm trọng + `exc_info=True` (unhandled, graph compile fail) |

**Coverage — 17 modules:**

```
[ChatController]  POST/GET nhận vào, 401, timeout, lỗi, SSE complete
[ChatService]     handle_chat, stream_chat, graph complete (latency/iter), persist
[RateLimit]       429 | ip | count/100 | retry_after
[Graph]           compile start/complete, Redis setup, error_handler triggered
[Router]          routing, max_iter exceeded, error_state, invalid node
[Orchestrator]    start, routing + intent, JSON fallback
[KR Agent]        start, query expanded, products found (top_score), error
[Psych Agent]     start, classification (state/confidence/strategy), JSON fallback
[Synth Agent]     start (N products, psych), complete (response_len, latency)
[GraphRAG]        entity graph loaded (node count), load failure
[HybridSearch]    start, per-collection hits (DEBUG), candidates, returned, latency
[Embeddings]      model init, embed_documents count (DEBUG)
[VectorDB]        client init, upsert/add/update/delete/query/count
[ConvRepo]        new/existing session, message logged, session updated
[Exception]       AppException (WARNING), unhandled (ERROR + exc_info), validation
[DBManager]       init_all complete
[ModelFactory]    model init, missing env var
```

---

## 11. Configuration

**File:** `core/config.py` — pydantic-settings, tự load từ `.env`

```env
APP_NAME=Pancharm AI Retail Consultant

# LLM
ANTHROPIC_API_KEY=...
ANTHROPIC_MODEL_PRIMARY=claude-sonnet-4-6
ANTHROPIC_MODEL_FAST=claude-haiku-4-5-20251001
OPENAI_API_KEY=...

# PostgreSQL (primary)
PG_HOST=localhost | PG_PORT=5432 | PG_NAME=ai-chatbot
PG_USER=admin    | PG_PASSWORD=... | PG_POOL_SIZE=10 | PG_MAX_OVERFLOW=20

# ChromaDB
CHROMA_PATH=./chroma_db

# Redis
REDIS_HOST=localhost | REDIS_PORT=6379 | REDIS_PASSWORD=

# Auth (JWT)
SECRET_KEY=pancharm_mas_secret
ALGORITHM=HS512
ACCESS_TOKEN_EXPIRE_MINUTES=120
REFRESH_TOKEN_EXPIRE_MINUTES=30

# CORS
ALLOWED_ORIGINS=["http://localhost:5173"]

# MinIO
MINIO_ENDPOINT=localhost:9002 | MINIO_ACCESS_KEY=admin | MINIO_SECRET_KEY=...

# LangSmith (optional)
LANGCHAIN_TRACING_V2=false | LANGCHAIN_API_KEY=... | LANGCHAIN_PROJECT=pancharm-mas
```

---

## 12. API Endpoints

| Method | Path | Auth | Timeout | Mô tả |
|--------|------|------|---------|-------|
| `POST` | `/api/v1/chat` | Bearer JWT (required) | 30s | Đồng bộ — `ApiResponse[ChatResponse]` |
| `GET` | `/api/v1/chat/stream` | Bearer JWT (optional) | — | SSE — true token streaming |
| `GET` | `/api/v1/sample/check` | — | — | Health check mẫu |
| `GET` | `/` | — | — | App info JSON |
| `GET` | `/health` | — | — | `{"status": "healthy"}` |

**Request:**
```json
{
  "session_id": "uuid-v4 (optional)",
  "message":    "string (required)",
  "channel":    "web|mobile|facebook|zalo|tiktok",
  "user_id":    "integer (optional)"
}
```

**Response (`POST /chat`):**
```json
{
  "code": 200, "message": "Success",
  "result": {
    "session_id": "uuid-v4",
    "response": "AIDA-structured Vietnamese text",
    "psych_state": "CURIOUS|INTERESTED|HESITATION|COMMITTED|OBJECTING",
    "psych_confidence": 0.82,
    "consult_strategy": "...",
    "retrieved_product_count": 5,
    "latency_ms": 1234.56,
    "iteration_count": 3
  }
}
```

**SSE Events (`GET /chat/stream`):**
```
data: {"token": "Xin", "done": false}
data: {"token": " chào", "done": false}
...
data: {"done": true, "session_id": "...", "psych_state": "...", "latency_ms": 1234.56}
```

---

## 13. Constants & Hyperparameters

**File:** `common/constants.py`

```python
MAX_ITERATIONS   = 8       # vòng lặp tối đa Orchestrator trước khi force END
LAMBDA_DENSE     = 0.50    # trọng số cosine similarity
LAMBDA_SPARSE    = 0.30    # trọng số BM25
LAMBDA_META      = 0.20    # trọng số metadata filter
MMR_LAMBDA       = 0.7     # relevance vs diversity balance
TOP_K_INITIAL    = 20      # candidates trước re-ranking
TOP_K_FINAL      = 5       # kết quả cuối trả cho Synth Agent
SESSION_TTL      = 3600    # Redis TTL (giây)
RATE_LIMIT_RPM   = 100     # requests/minute per IP — enforced by RateLimitMiddleware
EMBEDDING_MODEL  = "text-embedding-3-small"
EMBEDDING_DIMS   = 1536
```

---

## 14. Startup Sequence

```
uvicorn main:app
    │
    ▼ Middleware registration (outermost → innermost):
    │   1. RateLimitMiddleware (mới)
    │   2. CORSMiddleware
    │
    ▼ FastAPI lifespan(app):
    ├── load_dotenv()
    ├── get_compiled_graph()  ← pre-warm
    │     ├── [Graph] Redis checkpointer ready
    │     └── [Graph] Compilation complete
    │
    ▼ App ready tại http://0.0.0.0:8088
    │
    ▼ First request (lazy init):
    ├── [GraphRAG] Entity graph loaded | nodes=17 | path=resources/data/entity_graph.json
    ├── [Embeddings] Initializing model=text-embedding-3-small dims=1536
    ├── [VectorDB] Initializing ChromaDB PersistentClient
    └── [VectorDB] ChromaDB client ready
```

---

## 15. Điểm Kiến Trúc Đặc Biệt (Thesis Contributions)

| # | Đặc điểm | Ý nghĩa |
|---|----------|---------|
| 1 | **Psych Agent là first-class agent** | Node đầy đủ trong DCG, continuously shaping consultation strategy — không phải post-hoc classifier |
| 2 | **Reducer-based state merge** | Mỗi agent chỉ trả delta, LangGraph merge theo reducer. Agents hoàn toàn decoupled |
| 3 | **Dual-memory architecture** | Redis (short-term, 1h) cho context window; PostgreSQL (permanent) cho analytics |
| 4 | **Fire-and-forget DB persistence** | `asyncio.create_task()` — DB write không block response latency |
| 5 | **Zero-shot psych classification** | Không cần annotated data — critical cho tiếng Việt khan hiếm labeled data |
| 6 | **Graph RAG + Hybrid Search** | 3-stage: JSON entity expansion → Dense+BM25+Meta → MMR |
| 7 | **Multi-granularity ChromaDB** | 3 collections phục vụ 3 loại truy vấn (general/technical/trust) |
| 8 | **Conditional DCG** | Vòng lặp có kiểm soát (MAX_ITERATIONS=8) cho phép Orchestrator gọi nhiều agent/turn |
| 9 | **True SSE token streaming** | `astream_events(v2)` + async synth_agent dùng `astream` — latency to first token thấp hơn đáng kể |

---

## 16. Backlog

### Đã triển khai

| Hạng mục | Ngày | Chi tiết |
|----------|------|---------|
| Rate limiting middleware | 2026-06-12 | `middleware/rate_limit_middleware.py` — sliding window 100 RPM/IP |
| JWT Auth | 2026-06-12 | `core/security.py` + `api/deps.py` — require/optional auth trên chat endpoints |
| SSE true token streaming | 2026-06-12 | `synth_agent` async + `astream`, `ChatService.stream_chat()` dùng `astream_events` |
| Graph RAG từ JSON | 2026-06-12 | `resources/data/entity_graph.json` — editable không cần redeploy |

### Còn lại (liên quan PostgreSQL)

| Hạng mục | Độ ưu tiên | Ghi chú |
|----------|-----------|---------|
| ChromaDB data ingestion | HIGH | Cần script đọc từ PostgreSQL Products → embed → nạp vào 3 collections |
| AgentPerformanceLogs ghi | MEDIUM | Entity + table đã có, chưa ghi latency/tokens từ agents vào PostgreSQL |
| PsychStateLogs ghi | MEDIUM | Entity + table đã có, chưa ghi per-turn psych history vào PostgreSQL |
| `init_all()` trong startup | LOW | `DBManager.init_all()` chưa được gọi từ `main.py` lifespan |
