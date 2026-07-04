# Pancharm MAS — Tài Liệu Kiến Trúc & Tham Chiếu Dự Án

> **Tác giả:** Phan Tuấn Việt  
> **Cập nhật:** 2026-07-05 — phản ánh codebase hiện tại, bao gồm các tối ưu độ trễ phản hồi (Extraction Agent chạy song song, fix race condition, siết điều kiện tạo Order)  
> **Mục đích:** Nguồn tham chiếu duy nhất để hiểu ngữ cảnh, kiến trúc và trạng thái dự án mà không cần đọc toàn bộ codebase.

---

## 1. Tổng Quan Hệ Thống

**Pancharm AI Retail Consultant** là hệ thống Multi-Agent System (MAS) tư vấn bán lẻ trang sức phong thủy tiếng Việt, xây dựng trên nền LangGraph Directed Cyclic Graph (DCG). Hệ thống gồm 4 agent chuyên biệt phối hợp qua shared state, kết hợp retrieval 3 tầng và vòng học trực tuyến từ dữ liệu hội thoại thực.

| Thuộc tính | Giá trị |
|---|---|
| Domain | Tư vấn trang sức phong thủy — thị trường Việt Nam |
| Kiến trúc core | 4-agent MAS trên LangGraph DCG (7 nodes) |
| API framework | FastAPI 0.128+ / Uvicorn (ASGI) |
| LLM chính | `claude-sonnet-4-6` — Orchestrator, Synth Agent |
| LLM nhanh | `claude-haiku-4-5-20251001` — KR Agent, Psych Agent, Extraction Agent |
| Embedding | `paraphrase-multilingual-MiniLM-L12-v2` — local, 384 dims, multilingual |
| Vector DB | ChromaDB PersistentClient — 6 collections (HNSW cosine) |
| Relational DB | MySQL 8+ (SQLAlchemy 2.x + PyMySQL, pool_size=10) |
| Session checkpoint | Redis Stack → AsyncSQLite → MemorySaver (fallback chain) |
| Auth | Optional JWT Bearer (khách không cần đăng nhập) |
| Rate limit | 100 RPM/IP — RateLimitMiddleware sliding window |
| Python | 3.11+ |

**Luồng chính:**
```
Khách hàng nhắn tin (API / Telegram / Messenger / Zalo)
  → FastAPI → ChatService → LangGraph Graph
  → Orchestrator (định tuyến)
  → KR Agent (tìm sản phẩm) + Psych Agent (phân tích tâm lý)
  → Synth Agent (tổng hợp câu trả lời streaming)
  → SSE response → DB persist (async background)
```

---

## 2. Kiến Trúc Phân Tầng

```
┌──────────────────────────────────────────────────────────────────────┐
│  CLIENT  (Web · Mobile · Telegram · Zalo · Facebook Messenger)       │
└─────────────────────────────┬────────────────────────────────────────┘
                              │ HTTP REST / SSE Stream
┌─────────────────────────────▼────────────────────────────────────────┐
│  MIDDLEWARE (Starlette)                                               │
│  ① RateLimitMiddleware  — 100 RPM/IP, sliding window                │
│  ② CORSMiddleware       — allowed_origins từ settings               │
└─────────────────────────────┬────────────────────────────────────────┘
                              │
┌─────────────────────────────▼────────────────────────────────────────┐
│  API LAYER  (FastAPI)                                                 │
│  POST /api/v1/chat          — sync response                          │
│  GET  /api/v1/chat/stream   — SSE streaming token-by-token           │
│  POST /api/v1/webhook/*     — Telegram / Zalo / Messenger            │
│  GET  /health               — readiness probe (MySQL + ChromaDB)     │
└─────────────────────────────┬────────────────────────────────────────┘
                              │
┌─────────────────────────────▼────────────────────────────────────────┐
│  SERVICE LAYER                                                        │
│  ChatService        — graph invocation, order sync, stream SSE       │
│  BusinessService    — background: logs, user upsert, ChromaDB train  │
└────────────┬───────────────────────────────┬─────────────────────────┘
             │ ainvoke / astream_events       │ asyncio.create_task (bg)
┌────────────▼───────────────┐  ┌────────────▼─────────────────────────┐
│  LANGGRAPH MAS (DCG)       │  │  DATA LAYER                          │
│  7 nodes — xem §3          │  │  MySQL  — 25 ORM entities            │
│  Redis checkpoint          │  │  ChromaDB — 6 collections            │
└────────────────────────────┘  └──────────────────────────────────────┘
```

---

## 3. LangGraph DCG — Sơ Đồ Node

```
                     START
                       │
               ┌───────▼────────┐
               │  orchestrator  │ ◄────────────────────┐
               │ (CoT routing)  │                       │
               └──┬──┬──┬──┬───┘                       │
                  │  │  │  │                            │
       ┌──────────┘  │  │  └──────────┐                │
       │             │  │             │                 │
  ┌────▼────┐  ┌─────▼──┐  ┌─────────▼──┐  ┌─────────▼──┐
  │kr_agent │  │psych_  │  │order_lookup│  │error_      │
  │(search) │  │agent   │  │(DB query)  │  │handler     │
  └────┬────┘  └────┬───┘  └─────────┬──┘  └─────────┬──┘
       │            │                │               │
       └────────────┘                │               │
            │ next_node=orchestrator  │               │
            └──────────────►(back)   │               │
                                     │               │
                     ┌───────────▼────────────┐        │
                     │  fan-out song song      │        │
                     │  (router trả về list)   │        │
                     └──┬──────────────────┬───┘        │
                        │                  │             │
                 ┌──────▼──────┐   ┌───────▼────────┐    │
                 │ synth_agent │   │extraction_agent│    │
                 │ (async SSE) │   │(structured parse)   │
                 └──────┬──────┘   └───────┬────────┘    │
                        │                  │              │
                        └────────► END ◄───┘──────────────┘
```

> **Tối ưu 2026-07-05:** `synth_agent` và `extraction_agent` trước đây chạy **tuần tự**
> (synth → extraction → END), khiến mỗi lượt chat phải chờ thêm 1 lệnh gọi LLM (Haiku)
> sau khi câu trả lời đã sẵn sàng — độ trễ cộng dồn không cần thiết vì Extraction Agent
> chỉ phục vụ ghi log/CRM, không ảnh hưởng nội dung trả lời. Đã đổi `conditional_router`
> (`graph/router.py`) để trả về `["synth_agent", "extraction_agent"]` khi routing tới
> Synth — LangGraph chạy cả hai đồng thời trong cùng một superstep, cả hai cùng merge
> về `END`. Latency mỗi lượt giảm từ `synth_time + extraction_time` xuống còn
> `max(synth_time, extraction_time)`. Vì 2 node chỉ ghi vào các field khác nhau của
> `ConversationState` (`final_response`/`messages` vs `extracted_info`), không có xung
> đột reducer khi merge. Đánh đổi nhỏ: Extraction Agent đọc lịch sử hội thoại tại thời
> điểm *trước* khi Synth thêm câu trả lời của bot vào state — chấp nhận được vì mọi
> trường trích xuất (SĐT, tên, order_intent...) đều dựa trên lời khách nói.

**Routing logic** — Orchestrator quyết định `next_node` qua Chain-of-Thought JSON:

| Điều kiện | Route |
|---|---|
| Intent = `order_status_check` | `order_lookup` |
| Intent = `general_chat` / `logistics_query` / `feng_shui_advice` | `synth_agent` |
| `retrieved_products` rỗng | `kr_agent` |
| Câu hỏi khác chủ đề sản phẩm hiện tại | `kr_agent` |
| `psych_confidence < 0.6` | `psych_agent` |
| Có đủ products + psych, chưa có response | `synth_agent` |
| `error_state` không null | `error_handler` |
| `iteration_count ≥ MAX_ITERATIONS (8)` | `synth_agent` (forced) |

**Vòng lặp tối đa:** 8 iterations (MAX_ITERATIONS).

---

## 4. Bốn Agent Chuyên Biệt

### 4.1 Orchestrator Agent

| Thuộc tính | Giá trị |
|---|---|
| Model | `claude-sonnet-4-6` |
| Temperature | 0.0 |
| Max tokens | 600 |
| Prompt | `resources/prompt/orchestrator_agent.md` |

**Trách nhiệm:** Phân tích intent → đánh giá state → ra quyết định routing. Là authority routing duy nhất — các agent không giao tiếp trực tiếp với nhau.

**Output JSON:**
```json
{
  "reasoning": "Bước 1...Bước 2...Bước 3...Bước 4",
  "user_intent": "product_inquiry",
  "next_node": "kr_agent"
}
```

**Intent types:** `product_inquiry`, `purchase_intent`, `order_status_check`, `logistics_query`, `feng_shui_advice`, `price_negotiation`, `complaint_feedback`, `general_chat`

---

### 4.2 KR Agent (Knowledge Retrieval)

| Thuộc tính | Giá trị |
|---|---|
| Model | `claude-haiku-4-5-20251001` |
| Temperature | 0.0 |
| Max tokens | 300 |
| Prompt | `resources/prompt/kr_agent.md` |

**3 giai đoạn:**

**① Query Expansion**
- Graph RAG: keyword matching → BFS 1-hop trong `resources/data/entity_graph.json`
- LLM expansion: Haiku sinh `enriched_query` + `metadata_filters` (JSON)
- Context-aware: nhận 2 lượt hội thoại trước để expand đúng ngữ cảnh (mệnh, dịp, ngân sách đã đề cập)

**② Hybrid Search** — Composite score:
```
score = 0.50 × dense + 0.30 × BM25 + 0.20 × metadata
```
- **Dense (0.50):** Cosine similarity trên ChromaDB HNSW (`product_overview`, `product_specs`, `product_reviews`)
- **BM25 (0.30):** Sparse matching với `unicodedata.normalize("NFC")` — fix encoding dấu tiếng Việt
- **Metadata (0.20):** Soft scoring (tỷ lệ filter thỏa / tổng filter — không loại hoàn toàn sản phẩm gần đúng)

**③ MMR Re-ranking** — Maximal Marginal Relevance:
```
score(d) = 0.7 × relevance(d, q) − 0.3 × max_sim(d, selected)
```
- TOP_K_INITIAL = 20 candidates → MMR chọn TOP_K_FINAL = 5 → Synth Agent

---

### 4.3 Psych Agent (Psychology Classification)

| Thuộc tính | Giá trị |
|---|---|
| Model | `claude-haiku-4-5-20251001` |
| Temperature | 0.0 |
| Max tokens | 500 |
| Prompt | `resources/prompt/psych_agent.md` |

**5 trạng thái tâm lý (PsychState enum):**

| State | Định nghĩa | Chiến lược Synth |
|---|---|---|
| `CURIOUS` | Khám phá thụ động, chưa có mục tiêu | Hỏi 2 câu clarifying, ≤ 60 từ |
| `INTERESTED` | Quan tâm sản phẩm cụ thể | Storytelling, ≤ 130 từ |
| `HESITATION` | Phân vân — giá/chất lượng/thương hiệu | Feel-Felt-Found, ≤ 160 từ |
| `COMMITTED` | Sẵn sàng mua | Xác nhận + CTA rõ ràng, ≤ 80 từ |
| `OBJECTING` | Phản bác tích cực | Đồng cảm + tái định vị, ≤ 150 từ |

**Output JSON:**
```json
{
  "psych_state": "HESITATION",
  "psych_confidence": 0.88,
  "primary_concern": "Lo ngại về giá — vượt ngân sách dự kiến",
  "consult_strategy": "Feel-Felt-Found: đồng cảm → bình thường hóa → đề xuất trả góp"
}
```

**Fallback:** JSON parse fail → default `CURIOUS` + `confidence=0.65` (trên ngưỡng 0.6 để tránh vòng lặp Orchestrator → psych_agent)

---

### 4.4 Synth Agent (Response Synthesis)

| Thuộc tính | Giá trị |
|---|---|
| Model | `claude-sonnet-4-6` |
| Temperature | 0.3 (thấp — factual grounding ưu tiên) |
| Max tokens | 400 |
| Prompt | `resources/prompt/synth_agent.md` |

**Context được truyền vào:**
1. Lịch sử hội thoại 3 lượt gần nhất (tránh lặp intro)
2. Tin nhắn hiện tại + intent + lượt thứ mấy
3. Psych state + consult_strategy + primary_concern
4. Sản phẩm top-3 (tên, giá, mô tả 120 ký tự)
5. *(Khi có đủ ≥ 3 sessions thành công)* 1 transcript tương tự từ `training_sessions_success`

**Cấu trúc AIDA:** Attention → Interest → Desire → Action (CTA calibrated theo psych_state)

**3 ràng buộc bất biến:**
- Factual Grounding: chỉ dùng thông tin từ KR Agent — zero hallucination
- Strategy Alignment: conform với `consult_strategy` từ Psych Agent
- Natural Tone: tiếng Việt thân thiện, không phải ngôn ngữ marketing sáo rỗng

---

### 4.5 Extraction Agent (Structured Parsing)

| Thuộc tính | Giá trị |
|---|---|
| Model | `claude-haiku-4-5-20251001` |
| Temperature | 0.0 |
| Max tokens | 400 |
| Chạy khi | **Song song với Synth Agent** (fan-out từ Orchestrator — xem §3) — không chặn latency trả lời |

**Output JSON (extract từ 10 messages gần nhất):**
```json
{
  "customer_name": "Nguyễn Văn A",
  "customer_phone": "0912345678",
  "birth_year": 1992,
  "gender": "M",
  "preferences": {"color": "vàng", "metal": "bạc 925"},
  "selected_product_ids": [42, 17],
  "order_intent": true,
  "conversion_outcome": "purchase_confirmed",
  "confidence": 0.91
}
```

**Validation trước khi persist** (`_sanitize_extracted_info`):
- Phone phải match `^(0|\+84)[3-9]\d{8}$`
- `birth_year` phải trong `(1900, 2020)`
- `confidence` clamp về `[0.0, 1.0]`

---

## 5. Shared State — ConversationState

```python
class ConversationState(TypedDict):
    messages:           Annotated[list, add_messages]  # reducer: append, no-dup
    user_intent:        str
    retrieved_products: list[ProductDoc]               # overwrite mỗi lượt KR
    retrieval_scores:   list[float]
    psych_state:        PsychState                     # enum 5 states
    psych_confidence:   float                          # [0.0, 1.0]
    primary_concern:    str | None
    consult_strategy:   str
    session_metadata:   Annotated[dict, _merge_dicts]  # reducer: merge fields
    final_response:     str
    next_node:          str
    error_state:        str | None                     # trigger error_handler nếu != None
    iteration_count:    int
    extracted_info:     dict | None
```

---

## 6. Database Layer

### 6.1 MySQL — Relational DB (25 entities)

```
Core Product:   Brand, Category, Tag, Product, ProductImage, ProductTag
User:           User, UserProfile, UserAddress
Commerce:       Cart, CartItem, Order, OrderItem, Payment
Content:        ProductReview
AI/Consult:     ConversationSession, ConversationMessage,
                PsychStateLog, AgentPerformanceLog
Platform:       APIKey, SystemConfig, AuditLog
```

| Bảng | Mục đích | Key columns |
|---|---|---|
| `conversation_sessions` | 1 row/phiên chat | `thread_id` (FK LangGraph), `conversion_outcome`, `final_psych_state` |
| `conversation_messages` | Mỗi turn user/bot | `role`, `content`, `agent_name`, `latency_ms` |
| `orders` | Đơn hàng từ chatbot | `order_code` (CHAT-YYYYMMDD-XXXXXX), `conversation_session_id` |
| `psych_state_logs` | ML training data | `psych_state`, `confidence_score`, `consult_strategy` |
| `agent_performance_logs` | Monitoring | `agent_name`, `latency_ms`, `retrieval_score` |

**Connection pool:** `pool_size=10`, `max_overflow=20`, `pool_pre_ping=True`, `charset=utf8mb4`

---

### 6.2 ChromaDB — Vector DB (6 collections)

**Product collections** (indexed khi seeding):

| Collection | Chunk size | Overlap | Mục đích |
|---|---|---|---|
| `product_overview` | 256 tokens | 32 | Query tổng quát |
| `product_specs` | 512 tokens | 64 | Chi tiết kỹ thuật |
| `product_reviews` | 384 tokens | 48 | Trust/trải nghiệm |

**Training collections** (populated live từ conversation):

| Collection | Khi nào ghi | Nội dung | Dùng để |
|---|---|---|---|
| `training_conversations` | Mỗi turn | `[Khách]: ...\n[Bot]: ...` | Future fine-tuning |
| `training_psych_labels` | Mỗi turn | User message + psych label | Psych model training |
| `training_sessions_success` | Khi sale thành công | Full transcript → chốt đơn | Few-shot cho Synth Agent |

**Embedding:** `paraphrase-multilingual-MiniLM-L12-v2` — 384 dims, cosine space, ~420MB local model

---

## 7. Vòng Học Trực Tuyến (Online Learning Loop)

```
Khách chốt đơn thành công
         │
         ▼
BusinessService._upsert_session_success_training()
         │
         ▼
ChromaDB: training_sessions_success
(indexed bằng embedding của user queries đầu phiên)
         │
         ▼
Phiên chat mới — query tương tự
         │
         ▼
Synth Agent: _get_similar_success_example()
(chỉ activate khi ≥ 3 sessions tích lũy)
         │
         ▼
Inject vào prompt: "Ví dụ phiên tư vấn thành công tương tự"
         │
         ▼
Synth Agent học tone, flow, cách chốt
         │
         ▼
Tỷ lệ chốt cao hơn → thêm training data → vòng lặp tiếp tục
```

---

## 8. API Endpoints

### Chat (Core)
| Method | Path | Mô tả |
|---|---|---|
| `POST` | `/api/v1/chat` | Sync response — trả ChatResponse đầy đủ |
| `GET` | `/api/v1/chat/stream` | SSE streaming — token-by-token từ Synth Agent |

> **Fix 2026-07-05:** `stream_chat()` trước đây chỉ persist tin nhắn, **bỏ sót toàn bộ
> business logic** (extraction, tạo Order, ghi `PsychStateLogs`/`AgentPerformanceLogs`,
> ChromaDB training data) — chỉ `handle_chat()` (đường sync) có đầy đủ. Đã tách phần xử
> lý sau-graph thành `ChatService._post_process_turn()` dùng chung cho cả hai, nên giờ
> `stream_chat` có đầy đủ side-effect tương đương `handle_chat`, chỉ khác cách trả nội
> dung (token-by-token vs full response).

**ChatRequest:**
```json
{
  "session_id": "uuid-hoặc-null",
  "message": "Tôi muốn mua vòng tay phong thủy",
  "channel": "web",
  "user_id": null
}
```

**ChatResponse:**
```json
{
  "session_id": "abc-123",
  "response": "Dạ em có thể giúp anh/chị...",
  "psych_state": "CURIOUS",
  "psych_confidence": 0.82,
  "consult_strategy": "Hỏi về mệnh và dịp",
  "retrieved_product_count": 5,
  "latency_ms": 1243.5,
  "iteration_count": 3
}
```

### Webhooks (Multi-platform)
| Method | Path | Platform |
|---|---|---|
| `POST` | `/api/v1/webhook/telegram` | Telegram Bot API |
| `POST` | `/api/v1/webhook/zalo` | Zalo OA |
| `POST` | `/api/v1/webhook/messenger` | Facebook Messenger |

### System
| Method | Path | Mô tả |
|---|---|---|
| `GET` | `/health` | Readiness probe — kiểm tra MySQL + ChromaDB thực tế |
| `GET` | `/` | API info |

---

## 9. Session Checkpoint Strategy

```python
# Fallback chain (graph/graph.py)
1. AsyncRedisSaver   — Redis Stack (production, FT._LIST probe)
2. AsyncSqliteSaver  — data/checkpoints.db (dev/thesis, đã có sẵn)
3. MemorySaver       — in-memory (stateless fallback)
```

`thread_id = session_id` → mỗi session có checkpoint riêng → LangGraph tự inject lịch sử messages khi `ainvoke`.

---

## 10. Background Task Pipeline

`extracted_info` giờ đã sẵn có ngay khi graph hoàn tất (Extraction Agent chạy song song
với Synth Agent trong graph — xem §3), nên `ChatService._post_process_turn()` (dùng
chung cho cả `handle_chat` và `stream_chat`) dispatch 2 background task chạy song song,
không ảnh hưởng response latency:

```
graph.ainvoke()/astream_events() hoàn tất (đã có final_response + extracted_info)
      │
      ├─► asyncio.create_task(_safe_task(persist_turn_async, ...))
      │         └── ConversationSession upsert (savepoint + SELECT FOR UPDATE — race-safe)
      │         └── ConversationMessage × 2 (user + assistant)
      │         └── Session.total_turns++
      │
      └─► asyncio.create_task(_safe_task(process_turn_async, ...))
                └── PsychStateLog insert
                └── AgentPerformanceLog insert
                └── User / UserProfile upsert (nếu extract được)
                └── Order + OrderItems (nếu đủ điều kiện "purchased" — xem §11)
                └── ChromaDB per-turn training upsert
                └── ChromaDB session success upsert (nếu order tạo thành công)
```

*Tất cả exceptions trong background task được log ở level `ERROR` với `exc_info=True` — không silently fail.*

> **Fix race condition 2026-07-05:** `ConversationRepository.upsert_session()` có thể bị
> gọi đồng thời bởi 2 task nền cho cùng `thread_id` (lượt đầu tiên của 1 session mới).
> Task thua race gặp `IntegrityError` (trùng `thread_id` unique) rồi re-SELECT để lấy
> session vừa được task kia tạo — nhưng dưới **MySQL REPEATABLE READ** (mặc định),
> transaction đó vẫn dùng snapshot cũ từ trước khi record kia tồn tại, nên SELECT
> thường vẫn trả về `None` → lỗi `'NoneType' object has no attribute 'id'` ở các bước
> sau. Đã sửa bằng cách re-SELECT với **`.with_for_update()`** (locking read) — đọc
> đúng bản ghi mới nhất đã commit thay vì bị kẹt ở snapshot cũ.

---

## 11. Order Creation Flow

> **Fix 2026-07-05 — siết điều kiện tạo Order:** Trước đây hệ thống tạo Order thật +
> mã đơn chỉ dựa vào `order_intent = true`, và nếu Extraction Agent chưa xác định được
> sản phẩm cụ thể thì **tự động fallback lấy sản phẩm đầu tiên vừa retrieve được** —
> nghĩa là chỉ cần AI đoán nhầm ý định mua (vd câu hỏi "còn hàng không?") trong lúc
> khách còn đang hỏi thêm thông tin, hệ thống vẫn tạo đơn thật cho 1 sản phẩm ngẫu
> nhiên và trả mã đơn dù chưa có SĐT/địa chỉ giao hàng. Đã sửa: chỉ tạo Order khi đủ
> **cả 4 điều kiện** — `order_intent = true` **và** `conversion_outcome == "purchased"`
> (đúng định nghĩa phễu trong `resources/prompt/extraction_agent.md`: sản phẩm + SĐT +
> địa chỉ) **và** có `customer_phone` **và** có `selected_product_ids` tường minh từ
> Extraction Agent — bỏ hẳn fallback đoán sản phẩm (ở cả `chat_service.py` và
> `business_service.py`).

Khi đã đủ điều kiện trên:

```
graph.ainvoke()/astream_events() complete (có extracted_info)
       │
       ▼
điều kiện: order_intent=true AND conversion_outcome=="purchased"
           AND customer_phone AND selected_product_ids
       │
       ▼
chat_service._create_order_sync()  ← SYNCHRONOUS trước khi trả response
       │
       ├── ConversationSession upsert
       ├── User upsert (theo phone)
       ├── Order INSERT (order_code = CHAT-YYYYMMDD-XXXXXX)
       └── OrderItems INSERT (CHỈ sản phẩm khách chọn rõ ràng, không đoán)
       │
       ▼
final_response += "\n\n📦 Mã đơn hàng: CHAT-20260704-A1B2C3"
       │
       ▼
Trả response cho user (có mã đơn) — áp dụng cho cả handle_chat và stream_chat
       │
       ▼
Background: BusinessService nhận pre_created_order_id
            → bỏ qua bước tạo order (tránh duplicate)
```

---

## 12. Cấu Trúc Thư Mục

```
thesis/
├── main.py                          # FastAPI entry point + lifespan startup
├── database.sql                     # MySQL 8.0 DDL schema (25 bảng)
├── requirements.txt / .in           # Dependencies
├── .env / .env.example              # ⚠️ .env chứa API key thật — không được commit
│
├── agents/                          # 6 LangGraph agent nodes
│   ├── orchestrator_agent.py        # Sonnet 4.6 — routing CoT
│   ├── kr_agent.py                  # Haiku — hybrid search + Graph RAG
│   ├── psych_agent.py               # Haiku — psychology classification
│   ├── synth_agent.py               # Sonnet 4.6 — AIDA response synthesis
│   ├── extraction_agent.py          # Haiku — structured info extraction
│   └── order_lookup_node.py         # DB query — order status
│
├── graph/
│   ├── graph.py                     # DCG compilation + checkpoint setup
│   ├── router.py                    # conditional_router (điều kiện chuyển node)
│   └── state.py                     # ConversationState TypedDict + PsychState enum
│
├── retrieval/
│   ├── hybrid_search.py             # Dense(0.5) + BM25(0.3) + Meta(0.2) + MMR
│   ├── graph_rag.py                 # Entity graph BFS expansion
│   └── embeddings.py                # SentenceTransformer singleton (384 dims)
│
├── api/
│   ├── api_router.py                # Mount: /auth, /chat, /webhook
│   └── v1/endpoints/
│       ├── base/chat_controller.py  # POST /chat (sync), GET /chat/stream (SSE)
│       └── webhook/                 # Telegram / Messenger / Zalo
│
├── services/
│   ├── chat_service.py              # Graph invocation, SSE, order sync, _safe_task
│   └── business_service.py          # Background: training data, business logic
│
├── repositories/
│   ├── conversation_repository.py   # Session + message CRUD (savepoint + SELECT FOR UPDATE — race-safe)
│   └── business_repository.py       # Order, User, ML log CRUD
│
├── database/
│   ├── database.py                  # MySQL engine + SessionLocal (get_db)
│   ├── mysql_manager.py             # Đăng ký MySQL là "default"
│   └── vector_db_manager.py         # ChromaDB Singleton (PersistentClient)
│
├── entity/                          # 25 SQLAlchemy ORM models
│   ├── base_model.py                # Base, TimestampMixin, SoftDeleteMixin
│   ├── product.py, brand.py, category.py, tag.py
│   ├── product_image.py, product_review.py, product_doc.py
│   ├── user.py, user_profile.py, user_address.py
│   ├── cart.py, cart_item.py, order.py, order_item.py, payment.py
│   ├── conversation_session.py, conversation_message.py
│   ├── psych_state_log.py, agent_performance_log.py
│   └── api_key.py, audit_log.py, system_config.py
│
├── adapter/                         # Multi-platform bot adapters
│   ├── setup.py                     # Đăng ký adapter dựa theo token trong .env
│   ├── telegram_adapter.py
│   ├── messenger_adapter.py
│   └── zalo_adapter.py
│
├── messaging/
│   ├── consumer.py, producer.py     # aiokafka async consumer/producer
│   └── handler.py, topics.py
│
├── middleware/
│   └── rate_limit_middleware.py     # Sliding-window 100 RPM per IP
│
├── core/
│   ├── config.py                    # Pydantic Settings — tất cả env vars
│   ├── logger.py                    # coloredlogs + rotating file handler
│   └── security.py                  # JWT HS512
│
├── constants/constants.py           # MAX_ITERATIONS, Lambda weights, collection names
│
├── resources/
│   ├── prompt/                      # 5 agent system prompts (.md)
│   │   ├── orchestrator_agent.md
│   │   ├── kr_agent.md
│   │   ├── psych_agent.md
│   │   ├── synth_agent.md
│   │   └── extraction_agent.md
│   ├── data/
│   │   └── entity_graph.json        # Entity graph (ngũ hành, dịp lễ, loại SP, khoảng giá)
│   └── migrate/
│       └── seed.sql                 # Dữ liệu mẫu MySQL
│
├── data/
│   ├── checkpoints.db               # LangGraph AsyncSQLite checkpoint (đã có sẵn)
│   ├── checkpoints.db-shm
│   └── checkpoints.db-wal
│
├── scripts/
│   ├── seed_vectordb.py             # Đồng bộ MySQL → ChromaDB (3 collection sản phẩm)
│   └── reset_conversation_data.py   # Xóa dữ liệu hội thoại/checkpoint (MySQL + Redis + SQLite + ChromaDB training_*) để test lại từ đầu
│
├── logs/                            # app.log (rotating)
└── documents/                       # Tài liệu kỹ thuật luận văn
    ├── tai_lieu_ky_thuat_vi.md      # Tài liệu kỹ thuật tiếng Việt (15 phần)
    └── thesis_summary.md            # Tóm tắt kỹ thuật tiếng Anh (12 phần)
```

---

## 13. Environment Variables

### Bắt buộc (app crash nếu thiếu)

| Biến | Mục đích |
|---|---|
| `ANTHROPIC_API_KEY` | 5 agents (Orchestrator, KR, Psych, Synth, Extraction) |
| `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` | MySQL — lưu toàn bộ dữ liệu nghiệp vụ |

### Tùy chọn (degraded nhưng vẫn chạy nếu thiếu)

| Biến | Mục đích | Hành vi khi thiếu |
|---|---|---|
| `REDIS_HOST/PORT` | LangGraph checkpointer | Fallback → AsyncSQLite (`data/checkpoints.db`) |
| `KAFKA_BOOTSTRAP_SERVERS` | Async bot messaging | Skip, không ảnh hưởng chat |
| `TELEGRAM_BOT_TOKEN` | Telegram adapter | Adapter không đăng ký |
| `MESSENGER_PAGE_ACCESS_TOKEN` | Messenger adapter | Adapter không đăng ký |
| `ZALO_OA_ACCESS_TOKEN` | Zalo adapter | Adapter không đăng ký |
| `LANGCHAIN_API_KEY` | LangSmith tracing | Disabled mặc định |

---

## 14. Startup Sequence

```
1. load_dotenv()
2. BotMessageConsumer khởi tạo (chưa connect)
3. DBManager.init_all()
   └── MySQLManager.init() → tạo MySQL engine (pool_size=10)
4. init_db()  — tạo bảng nếu chưa tồn tại (Base.metadata.create_all)
5. get_compiled_graph()  — CRITICAL: fail → raise RuntimeError
   ├── _build_checkpointer():
   │   ├── Probe Redis Stack (FT._LIST)
   │   ├── Nếu không có Redis → AsyncSQLite (data/checkpoints.db)
   │   └── Nếu cả hai fail → MemorySaver
   └── _build_graph(): 7 nodes + edges → compile(checkpointer=...)
6. setup_adapters()
   └── Đăng ký Telegram/Messenger/Zalo nếu có token
7. Kafka: bot_producer.start() + _bot_consumer.start() (non-fatal nếu fail)
```

---

## 15. Dữ Liệu Mock — resources/migrate/seed.sql

| Bảng | Số bản ghi | Ghi chú |
|---|---|---|
| Brands | 10 | Pancharm, Kim Bảo Phong Thủy, Ngọc Thanh Jewelry... |
| Tags | 15 | Ngũ hành (Kim/Mộc/Thủy/Hỏa/Thổ), dịp lễ, loại sản phẩm |
| Categories | 12 | 3 cấp: Root → Sub (Vòng Tay, Nhẫn, Dây Chuyền, Hoa Tai...) |
| Products | 12 | Giá 380K–12M VND, đủ 6 nguyên tố, 5 loại trang sức |
| ProductImages | 20 | 2 ảnh/sản phẩm (main + detail) |
| Users | 12 | 10 khách + 1 admin + 1 staff |
| UserProfiles | 12 | Zodiac, mệnh, lịch sử chi tiêu, phân khúc loyalty |
| UserAddresses | 14 | HCM, Đà Nẵng, Huế, Cần Thơ |
| Orders | 12 | Vòng đời đầy đủ (pending → delivered) |
| OrderItems | 15 | Nhiều sản phẩm/đơn |
| Payments | 12 | MoMo, VNPay, ZaloPay, COD, bank transfer |
| ConversationSessions | 12 | Session chat thực tế với latency data |
| ConversationMessages | 20 | Transcript hội thoại đầy đủ |
| PsychStateLogs | 12 | Dữ liệu đánh giá CARS framework |
| AgentPerformanceLogs | 12 | Metrics từng agent |

**Chạy seed:**
```bash
mysql -u root -p ai_chatbot < database.sql
mysql -u root -p ai_chatbot < resources/migrate/seed.sql
```

---

## 16. Technology Stack

| Layer | Technology | Version | Ghi chú |
|---|---|---|---|
| API | FastAPI | 0.128+ | Async, SSE, OpenAPI tự động |
| ASGI | Uvicorn | 0.40+ | Production ASGI server |
| Agent orchestration | LangGraph | 1.2+ | DCG, shared state, checkpoint |
| LLM SDK | langchain-anthropic | 1.4+ | Haiku + Sonnet |
| Embedding | sentence-transformers | 5.4+ | Local — không cần API key |
| Vector DB | ChromaDB | 1.4+ | PersistentClient, HNSW |
| Sparse search | rank-bm25 | 0.2.2 | BM25Okapi |
| Relational DB | MySQL 8+ | — | utf8mb4 |
| ORM | SQLAlchemy | 2.0+ | Async-compatible |
| DB driver | PyMySQL | 1.1+ | Sync driver |
| Checkpoint (prod) | Redis Stack | 7+ | RediSearch module |
| Checkpoint (dev) | AsyncSQLite | built-in | LangGraph fallback |
| Message queue | Kafka + aiokafka | 0.14.0 | Bot message routing |
| Platform | Telegram / Zalo / Messenger | — | Multi-channel adapters |

---

## 17. Các Thông Số Quan Trọng

| Thông số | Giá trị | Nguồn gốc |
|---|---|---|
| `LAMBDA_DENSE` | 0.50 | Grid search Recall@5 (thesis §3.2.2) |
| `LAMBDA_SPARSE` | 0.30 | Grid search Recall@5 |
| `LAMBDA_META` | 0.20 | Grid search Recall@5 |
| `MMR_LAMBDA` | 0.7 | Relevance-heavy — catalog nhỏ (~200 SKU) |
| `TOP_K_INITIAL` | 20 | Đủ candidates cho BM25, tránh noise |
| `TOP_K_FINAL` | 5 | ~750 tokens context cho Synth Agent |
| `MAX_ITERATIONS` | 8 | Loop guard — tránh infinite routing |
| `psych_confidence` threshold | 0.6 | Ngưỡng re-route về psych_agent |
| Synth `max_tokens` | 400 | ~300 từ tiếng Việt — đủ theo word limit per state |
| Synth `temperature` | 0.3 | Factual grounding — giảm hallucination |
| Psych `max_tokens` | 500 | Đủ cho JSON output (consult_strategy dài) |
| KR `max_tokens` | 300 | Đủ cho enriched_query + metadata_filters JSON |
| `_MIN_SUCCESS_EXAMPLES` | 3 | Min sessions trước khi Synth dùng few-shot |

---

## 18. Checklist Chạy Lần Đầu

```
[ ] 1. pip install -r requirements.txt  (trong .venv)
[ ] 2. Copy .env.example → .env và điền API keys (ANTHROPIC_API_KEY, DB_*)
[ ] 3. Khởi động MySQL 8+ (local hoặc Docker)
[ ] 4. Chạy DDL + seed:
         mysql -u root -p ai_chatbot < database.sql
         mysql -u root -p ai_chatbot < resources/migrate/seed.sql
[ ] 5. Viết & chạy ingestion script để populate ChromaDB:
         - Đọc sản phẩm từ MySQL
         - Chunk theo 3 granularity (overview/specs/reviews)
         - Upsert vào 3 ChromaDB collections với embedding local
[ ] 6. python main.py  (uvicorn start trên port mặc định)
[ ] 7. Kiểm tra health: GET /health  → {"status": "healthy", "checks": {"mysql": "ok", "chromadb": "ok"}}
[ ] 8. Test chat: POST /api/v1/chat  {"message": "tôi muốn mua vòng tay phong thủy"}
[ ] 9. Kiểm tra SSE stream: GET /api/v1/chat/stream
```

---

## 19. Files Tham Chiếu Quan Trọng

| File | Nội dung |
|---|---|
| `agents/orchestrator_agent.py` | Logic routing chính của graph |
| `agents/kr_agent.py` | Hybrid search + ChromaDB query |
| `agents/synth_agent.py` | AIDA synthesis + few-shot retrieval |
| `graph/state.py` | Toàn bộ state schema + reducers |
| `core/config.py` | Tất cả env vars + defaults |
| `constants/constants.py` | Magic numbers (MAX_ITERATIONS, lambda weights...) |
| `resources/data/entity_graph.json` | Feng shui entity graph (Graph RAG) |
| `resources/prompt/orchestrator_agent.md` | System prompt Orchestrator |
| `resources/prompt/synth_agent.md` | System prompt Synth Agent (AIDA + word limits) |
| `database.sql` | MySQL DDL schema đầy đủ |
| `resources/migrate/seed.sql` | Mock data (18 bảng) |
| `data/checkpoints.db` | LangGraph checkpoint SQLite (đã có sẵn) |
| `documents/tai_lieu_ky_thuat_vi.md` | Tài liệu kỹ thuật tiếng Việt (15 phần) |

---

## 20. Tối Ưu Độ Trễ Phản Hồi (2026-07-05)

Ghi lại các thay đổi đã áp dụng và các hướng đã cân nhắc nhưng **từ chối có chủ đích**,
để tránh thử lại hướng đã biết không khả thi.

### 20.1 Đã áp dụng

| Thay đổi | File | Hiệu quả |
|---|---|---|
| Extraction Agent chạy **song song** với Synth Agent (fan-out qua router, xem §3) | `graph/router.py`, `graph/graph.py` | Latency/lượt giảm từ `synth + extraction` xuống `max(synth, extraction)` |
| `stream_chat()` dùng chung `_post_process_turn()` với `handle_chat()` | `services/chat_service.py` | Fix lỗ hổng: SSE stream trước đây bỏ sót toàn bộ business logic |
| Siết điều kiện tạo Order (bỏ fallback đoán sản phẩm) | `services/chat_service.py`, `services/business_service.py` | Đúng nghiệp vụ hơn — tránh side-effect sai, gián tiếp giảm rủi ro query/insert thừa |
| Fix race condition `upsert_session` bằng `SELECT ... FOR UPDATE` | `repositories/conversation_repository.py` | Tránh lỗi crash ở lượt đầu session mới (không phải tối ưu tốc độ, nhưng liên quan trực tiếp tới đường xử lý mỗi lượt chat) |
| Prompt caching (`cache_control: ephemeral`) | Tất cả 5 agent prompts | Đã có sẵn từ trước — giảm token xử lý cho system prompt lặp lại mỗi lượt |

### 20.2 Đã thử nhưng rollback — streaming (giả lập) cho Telegram

**Mục tiêu:** giảm độ trễ *cảm nhận* trên Telegram bằng cách stream token từ Synth Agent,
tương tự trải nghiệm ChatGPT/Claude web.

**Cách đã thử:** Telegram Bot API không có kênh token-stream thật (khác web SSE/WebSocket).
Mô phỏng bằng cách gửi 1 tin nhắn placeholder rồi gọi `editMessageText` lặp lại, throttle
~1 giây/lần để tránh flood-control của Telegram.

**Lý do rollback:** Telegram client phải **render lại toàn bộ bong bóng tin nhắn** mỗi lần
`editMessageText`, kết hợp với giới hạn tần suất edit (~1 lần/giây/chat) khiến trải nghiệm
bị giật/nhảy chữ — khác bản chất so với ChatGPT/Claude (client tự append DOM liên tục,
không giới hạn tần suất, không cần round-trip server). Đây là **giới hạn nền tảng, không
phải lỗi implementation** — nên không thử lại hướng edit-message này trừ khi Telegram
Bot API bổ sung cơ chế streaming mới.

**Kết luận:** với Telegram, nên tiếp tục dùng typing indicator (`sendChatAction`) +
gửi 1 tin nhắn hoàn chỉnh sau khi xử lý xong; muốn cải thiện UX chỉ nên tập trung vào
**giảm latency backend thực sự** (đã làm ở §20.1), không phải giả lập streaming ở tầng
adapter. Web (`/api/v1/chat/stream`, SSE) vẫn stream mượt bình thường vì không có giới
hạn này.

### 20.3 Hướng còn có thể khai thác (chưa làm)

- **Giảm số vòng lặp Orchestrator:** mỗi lượt chat có thể tốn 3-4 lệnh gọi Orchestrator
  (Sonnet — model "nặng") do vòng lặp `orchestrator → kr_agent/psych_agent → orchestrator`.
  Có thể rule-based hoá phần routing đơn giản (vd: chưa có `retrieved_products` → luôn
  `kr_agent` trước, không cần hỏi LLM) để giảm số lệnh gọi Sonnet/lượt.
- **Chạy `kr_agent` và `psych_agent` song song** (thay vì tuần tự qua orchestrator) khi
  cả hai đều cần thiết trong cùng lượt — tương tự kỹ thuật fan-out đã áp dụng cho
  Extraction Agent ở §20.1, có thể áp dụng lại cho cặp node này nếu router xác định cả
  hai đều cần chạy.
