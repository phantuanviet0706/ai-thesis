# Pancharm MAS — Tài Liệu Tham Chiếu Dự Án

> Cập nhật: 2026-06-27 | Scan bởi Claude Sonnet 4.6  
> Mục đích: File này là nguồn tham chiếu đầy đủ để hiểu ngữ cảnh, cấu trúc, và trạng thái dự án mà không cần đọc toàn bộ codebase.

---

## 1. Tổng Quan Dự Án

**Tên:** Pancharm Retail AI Consultation Platform  
**Loại:** Multi-Agent System (MAS) — luận văn tốt nghiệp FPT  
**Ngôn ngữ:** Python 3.11+  
**Stack chính:** FastAPI + LangGraph + ChromaDB + Claude API (Anthropic) + PostgreSQL  

**Bài toán:** Xây dựng chatbot tư vấn trang sức phong thủy tiếng Việt cho thương hiệu Pancharm. Hệ thống sử dụng 4 AI agent phối hợp để phân tích tâm lý khách hàng và gợi ý sản phẩm phù hợp theo ngũ hành.

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

## 2. Cấu Trúc Thư Mục

```
thesis/
├── main.py                          # FastAPI entry point + lifespan startup
├── database.sql                     # MySQL 8.0 DDL schema (17 bảng)
├── requirements.txt / .in           # ⚠️ Lưu dạng UTF-16LE — pip install sẽ fail (xem Bug #3)
├── mcp.config.json
├── .env                             # ⚠️ CHỨA API KEY THẬT — không được commit
├── .env.example
│
├── agents/                          # 4 LangGraph agents
│   ├── orchestrator.py              # Phân tích ý định + điều phối routing
│   ├── kr_agent.py                  # Knowledge Retrieval — tìm kiếm sản phẩm
│   ├── psych_agent.py               # Phân tích tâm lý khách hàng
│   └── synth_agent.py               # Tổng hợp câu trả lời (async streaming)
│
├── graph/
│   ├── graph.py                     # StateGraph assembly + checkpointer
│   ├── router.py                    # conditional_router (điều kiện chuyển node)
│   └── state.py                     # ConversationState TypedDict + PsychState enum
│
├── retrieval/
│   ├── hybrid_search.py             # Dense(0.5) + BM25(0.3) + Metadata(0.2) fusion + MMR
│   ├── chromadb_client.py           # Collection accessors
│   ├── embeddings.py                # OpenAI text-embedding-3-small (1536 dims)
│   └── graph_rag.py                 # Entity graph traversal (19 nodes)
│
├── api/
│   ├── api_router.py                # Mount: /auth, /chat, /sample, /webhook
│   ├── deps.py                      # optional_auth dependency
│   └── v1/endpoints/
│       ├── base/
│       │   ├── chat_controller.py   # POST /chat (sync+30s), GET /chat/stream (SSE)
│       │   ├── auth_controller.py
│       │   └── sample_controller.py
│       └── webhook/
│           └── webhook_controller.py  # Telegram / Messenger / Zalo webhooks
│
├── services/
│   ├── chat_service.py              # handle_chat(), stream_chat(), _persist_turn()
│   ├── auth_service.py
│   └── base_service.py
│
├── database/
│   ├── __init__.py                  # Standalone PG engine + get_db() (SessionLocal)
│   ├── database.py                  # DBManager factory (multi-engine registry)
│   ├── postgres_manager.py          # Đăng ký PG là "default" + "postgres"
│   ├── mysql_manager.py             # Đăng ký MySQL là "mysql" (optional)
│   └── vector_db_manager.py         # ChromaDB singleton (PersistentClient)
│
├── repositories/
│   ├── conversation_repository.py   # upsert_session, log_message, update_session_after_turn
│   ├── user_repository.py
│   ├── base_repository.py
│   └── sample_repository.py
│
├── entity/                          # 20+ SQLAlchemy ORM models
│   ├── base_model.py                # Base, TimestampMixin, SoftDeleteMixin, ActiveMixin
│   ├── product.py, brand.py, category.py, tag.py, product_tag.py
│   ├── product_image.py, product_review.py, product_doc.py
│   ├── user.py, user_profile.py, user_address.py
│   ├── cart.py, cart_item.py, order.py, order_item.py, payment.py
│   ├── conversation_session.py, conversation_message.py
│   ├── psych_state_log.py, agent_performance_log.py
│   ├── api_key.py, audit_log.py, system_config.py
│   └── sample_model.py
│
├── adapter/                         # Multi-platform bot adapters
│   ├── setup.py                     # Đăng ký adapter dựa theo token có trong .env
│   ├── registry.py
│   ├── base_adapter.py
│   ├── telegram_adapter.py
│   ├── messenger_adapter.py
│   └── zalo_adapter.py
│
├── infrastructure/
│   ├── redis_client.py              # Redis connection pool (sync)
│   └── kafka_client.py
│
├── messaging/
│   ├── consumer.py, producer.py     # aiokafka async consumer/producer
│   ├── handler.py, topics.py
│   └── __init__.py
│
├── middleware/
│   └── rate_limit_middleware.py     # Sliding-window 100 RPM per IP (in-memory)
│
├── core/
│   ├── config.py                    # Pydantic Settings — tất cả env vars
│   ├── logger.py                    # coloredlogs + rotating file handler
│   └── security.py                  # JWT HS512
│
├── schemas/                         # Pydantic request/response models
├── constants/                       # MAX_ITERATIONS=8, Lambda weights, collection names
├── exceptions/                      # AppException + global handler
├── utils/helper.py                  # read_file_contents(), extract_json()
├── models/                          # LLM provider abstractions (không dùng trong main path)
│
├── resources/
│   ├── prompt/                      # 4 system prompt markdown files
│   │   ├── orchestrator_agent.md
│   │   ├── kr_agent.md
│   │   ├── psych_agent.md
│   │   └── synth_agent.md
│   ├── data/
│   │   └── entity_graph.json        # 19-node entity graph (ngũ hành, dịp lễ, loại SP)
│   ├── migrate/
│   │   └── seed.sql                 # Dữ liệu mẫu MySQL (12 SP, 12 user, 12 đơn hàng...)
│   ├── summary/                     # Các file tóm tắt kiến trúc từ session trước
│   └── summary.md                   # ← FILE NÀY
│
├── data/
│   ├── checkpoints.db               # LangGraph AsyncSQLite checkpoint (đã có sẵn)
│   ├── checkpoints.db-shm
│   └── checkpoints.db-wal
│
├── logs/                            # app.log (rotating)
├── documents/                       # Luận văn PDF + tài liệu kỹ thuật
└── .venv/                           # Virtual environment
```

---

## 3. Kiến Trúc LangGraph

### Topology (Directed Cyclic Graph)

```
START
  ↓
orchestrator  ←──────────────────────────────┐
  ↓ (conditional_router đọc next_node)        │
  ├──→ kr_agent ──────────────────────────────┤
  ├──→ psych_agent ───────────────────────────┘
  ├──→ synth_agent ──→ END
  ├──→ error_handler ──→ END
  └──→ END
```

**Vòng lặp tối đa:** 8 iterations (MAX_ITERATIONS). Sau 8 vòng, router buộc END.

### Bảng Agent

| Agent | Model | Max Tokens | Temp | Vai trò |
|---|---|---|---|---|
| Orchestrator | `claude-sonnet-4-6` | 350 | 0.0 | Phân tích intent → JSON `{next_node, user_intent}` |
| KR Agent | `claude-haiku-4-5-20251001` | 180 | 0.0 | Mở rộng query → hybrid search ChromaDB |
| Psych Agent | `claude-haiku-4-5-20251001` | 200 | 0.0 | Phân loại 5 trạng thái tâm lý → chiến lược tư vấn |
| Synth Agent | `claude-sonnet-4-6` | 1024 | 0.7 | Async streaming response (AIDA framework) |

### ConversationState (TypedDict)

| Field | Reducer | Ghi bởi |
|---|---|---|
| `messages` | `add_messages` (append) | Tất cả agents |
| `user_intent` | overwrite | Orchestrator |
| `retrieved_products` / `retrieval_scores` | overwrite | KR Agent |
| `psych_state` / `psych_confidence` / `primary_concern` / `consult_strategy` | overwrite | Psych Agent |
| `session_metadata` | `_merge_dicts` (dict update) | ChatService |
| `final_response` | overwrite | Synth Agent |
| `next_node` | overwrite | Orchestrator |
| `error_state` | overwrite | Bất kỳ agent |
| `iteration_count` | `operator.add` (+1) | Orchestrator |

### 5 Trạng Thái Tâm Lý (PsychState Enum)

`CURIOUS` | `CONFUSED` | `CONCERNED` | `CONFIDENT` | `COMMITTED`

### Retrieval Pipeline

- **Hybrid search weights:** Dense 0.50 + BM25 0.30 + Metadata 0.20 (đã grid-search)
- **Top-K:** 20 candidates → MMR re-rank → top 5 truyền vào Synth Agent
- **3 ChromaDB collections per product:**
  - `product_overview` (chunk 256 tokens, overlap 32)
  - `product_specs` (chunk 512 tokens, overlap 64)
  - `product_reviews` (chunk 384 tokens, overlap 48)
- **Embedding:** OpenAI `text-embedding-3-small` (1536 dims)
- **Graph RAG:** `entity_graph.json` — 19 node (ngũ hành, dịp lễ, loại sản phẩm, khoảng giá)

---

## 4. Environment Variables

### Bắt buộc (app crash nếu thiếu)

| Biến | Mục đích |
|---|---|
| `ANTHROPIC_API_KEY` | 4 agents (Orchestrator, KR, Psych, Synth) |
| `OPENAI_API_KEY` | Embeddings (text-embedding-3-small) |
| `PG_HOST`, `PG_PORT`, `PG_USER`, `PG_PASSWORD`, `PG_NAME` | PostgreSQL — lưu hội thoại |

### Tùy chọn (degraded nhưng vẫn chạy nếu thiếu)

| Biến | Mục đích | Hành vi khi thiếu |
|---|---|---|
| `DB_HOST...DB_NAME` | MySQL secondary | init fail, không ảnh hưởng chat |
| `REDIS_HOST/PORT` | LangGraph checkpointer | Fallback → AsyncSQLite (`data/checkpoints.db`) |
| `KAFKA_BOOTSTRAP_SERVERS` | Async bot messaging | Skip, không ảnh hưởng chat |
| `TELEGRAM_BOT_TOKEN` | Telegram adapter | Adapter không đăng ký |
| `MESSENGER_PAGE_ACCESS_TOKEN` | Messenger adapter | Adapter không đăng ký |
| `ZALO_OA_ACCESS_TOKEN` | Zalo adapter | Adapter không đăng ký |
| `MINIO_ENDPOINT/ACCESS_KEY/SECRET_KEY` | File storage | Không dùng trong chat path |
| `LANGCHAIN_API_KEY` | LangSmith tracing | Disabled mặc định |

---

## 5. Dependencies Chính

> **Lưu ý:** `requirements.txt` và `requirements.in` hiện đang lưu dạng UTF-16LE — cần re-encode sang UTF-8 trước khi `pip install`.

| Package | Version | Mục đích |
|---|---|---|
| `fastapi` | 0.128.0 | HTTP framework |
| `uvicorn` | 0.40.0 | ASGI server |
| `langchain` | 1.3.9 | LLM orchestration |
| `langchain-anthropic` | 1.4.4 | Claude API adapter |
| `langchain-openai` | 1.1.7 | OpenAI embeddings |
| `langgraph` | 1.2.4 | Multi-agent state machine |
| `langgraph-checkpoint-sqlite` | 3.1.0 | AsyncSQLite fallback |
| `chromadb` | 1.4.1 | Vector database |
| `anthropic` | 0.109.1 | Direct Anthropic SDK |
| `openai` | 2.15.0 | Embeddings |
| `sqlalchemy` | 2.0.46 | ORM |
| `psycopg2` | 2.9.12 | PostgreSQL driver (⚠️ cần build tools — xem Bug #7) |
| `PyMySQL` | 1.1.2 | MySQL driver |
| `pydantic` | 2.12.5 | Validation |
| `rank-bm25` | 0.2.2 | BM25 sparse retrieval |
| `sentence-transformers` | 5.4.1 | (dự phòng, không dùng trong main path) |
| `torch` | 2.10.0 | Backend cho sentence-transformers |
| `redis` | 7.1.0 | Redis client |
| `aiokafka` | 0.14.0 | Kafka async |

---

## 6. Startup Sequence

```
1. load_dotenv()
2. BotMessageConsumer khởi tạo (chưa connect)
3. DBManager.init_all()
   ├── MySQLManager.init()    → tạo "mysql" engine (⚠️ crash nếu MySQL không chạy — xem Bug #2)
   └── PostgresManager.init() → tạo "default" + "postgres" engine
4. get_compiled_graph()
   ├── _build_checkpointer():
   │   ├── Probe Redis Stack (FT._LIST)
   │   ├── Nếu không có Redis → AsyncSQLite (data/checkpoints.db)
   │   └── Nếu cả hai fail → MemorySaver
   └── _build_graph(): 5 nodes + edges → compile(checkpointer=...)
5. setup_adapters()
   └── Đăng ký Telegram/Messenger/Zalo nếu có token
6. Kafka:
   ├── bot_producer.start()
   └── _bot_consumer.start()
   (try/except — non-fatal)
```

---

## 7. Dữ Liệu Mock — Trạng Thái & Đánh Giá

### Nội dung `resources/migrate/seed.sql`

| Bảng | Số bản ghi | Ghi chú |
|---|---|---|
| Brands | 10 | Pancharm, Kim Bảo Phong Thủy, Ngọc Thanh Jewelry... |
| Tags | 15 | Ngũ hành (Kim/Mộc/Thủy/Hỏa/Thổ), dịp lễ, loại sản phẩm |
| Categories | 12 | 3 cấp: Root → Sub (Vòng Tay, Nhẫn, Dây Chuyền, Hoa Tai...) |
| Products | 12 | Giá 380K–12M VND, đủ 6 nguyên tố, 5 loại trang sức |
| ProductImages | 20 | 2 ảnh/sản phẩm (main + detail), CDN URL |
| Users | 12 | 10 khách + 1 admin + 1 staff (local/Google/Facebook/Zalo auth) |
| UserProfiles | 12 | Zodiac, mệnh ưa thích, lịch sử chi tiêu, phân khúc loyalty |
| UserAddresses | 14 | Địa chỉ thực tế (HCM, Đà Nẵng, Huế, Cần Thơ) |
| Orders | 12 | Vòng đời đầy đủ (pending → delivered) |
| OrderItems | 15 | Nhiều sản phẩm/đơn |
| Payments | 12 | MoMo, VNPay, ZaloPay, COD, bank transfer, credit card |
| ConversationSessions | 12 | Session chat thực tế với latency data |
| ConversationMessages | 20 | Transcript hội thoại đầy đủ |
| PsychStateLogs | 12 | Dữ liệu đánh giá CARS framework |
| AgentPerformanceLogs | 12 | Metrics từng agent |
| APIKeys | 10 | Platform management |
| SystemConfigs | 20 | Cấu hình hệ thống |
| AuditLogs | 12 | Nhật ký audit |

**Đánh giá:** Dữ liệu mock **đầy đủ và chất lượng luận văn** — đủ đa dạng về sản phẩm, người dùng, đơn hàng, và dữ liệu đánh giá hệ thống.

### Khả Năng Migrate Sang DB Thật

#### MySQL 8.0 → **Sẵn sàng ngay**
- `database.sql` là DDL MySQL hoàn chỉnh (17 bảng)
- `seed.sql` tương thích MySQL native
- Thực thi trực tiếp: `mysql -u root -p ai_chatbot < database.sql && mysql -u root -p ai_chatbot < resources/migrate/seed.sql`

#### PostgreSQL → **Cần chuyển đổi**

Việc cần làm để migrate sang PostgreSQL:

**Schema (DDL):**
- Cách nhanh nhất: gọi `Base.metadata.create_all(engine)` trong `PostgresManager.init()` — SQLAlchemy ORM models trong `entity/` đã tương thích PostgreSQL
- Không cần convert `database.sql` thủ công

**Seed data:**
```sql
-- Xóa 2 dòng này (MySQL-only):
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- Thêm vào cuối để reset sequences:
SELECT setval('brands_id_seq', (SELECT MAX(id) FROM brands));
SELECT setval('products_id_seq', (SELECT MAX(id) FROM products));
-- ... lặp cho mỗi bảng có ID sequence
```
- `TRUE/FALSE` literals: đã tương thích PostgreSQL
- `AUTO_INCREMENT` trong DDL: không cần xử lý nếu dùng `create_all()` (SQLAlchemy tự dùng `SERIAL`/`BIGSERIAL`)

---

## 8. Đánh Giá Runability — Luồng Hoàn Chỉnh

### Kết luận: **CÓ THỂ CHẠY** nhưng cần giải quyết 2 blocker cứng

| # | Blocker | Độ ưu tiên | Cách fix |
|---|---|---|---|
| 1 | PostgreSQL schema chưa được tạo | **CRITICAL** | Thêm `Base.metadata.create_all(engine)` vào `PostgresManager.init()` |
| 2 | ChromaDB collections rỗng | **CRITICAL** | Viết ingestion script: đọc sản phẩm → chunk → upsert vào 3 collections |
| 3 | `requirements.txt` UTF-16LE | **HIGH** | Re-save dạng UTF-8 để `pip install` không fail |

### Non-blockers (degraded nhưng vẫn chạy)

| Điều kiện | Hành vi |
|---|---|
| MySQL không chạy | MySQLManager init fail — non-fatal cho chat flow |
| Redis không chạy | Fallback sang AsyncSQLite (`data/checkpoints.db` đã có sẵn) |
| Kafka không chạy | Bot messaging disable — chat API vẫn hoạt động |
| Không có platform tokens | Adapter không đăng ký — direct API call vẫn OK |

### Luồng E2E khi đã đủ điều kiện

```
POST /api/v1/chat/
  → ChatService.handle_chat() / stream_chat()
  → LangGraph graph.ainvoke() / astream()
  → Orchestrator (phân tích intent → next_node)
  → KR Agent (query expansion → ChromaDB hybrid search → top 5 products)
  → Psych Agent (phân loại tâm lý → consult_strategy)
  → Orchestrator (routing → synth_agent)
  → Synth Agent (AIDA streaming response)
  → StreamingResponse (SSE) → client
  → asyncio.create_task(_persist_turn()) → PostgreSQL
```

---

## 9. Bugs & Issues Đã Phát Hiện

### Bug #1 — Double PostgreSQL engine (không crash, nhưng lãng phí)
- `database/__init__.py` tạo engine riêng tại import time
- `database/postgres_manager.py` tạo thêm engine thứ 2 cùng DB
- `ChatService` dùng `get_db()` từ `__init__.py`, không dùng `DBManager`
- Kết quả: 2 connection pool song song đến cùng 1 PostgreSQL DB

### Bug #2 — MySQLManager crash startup nếu MySQL không chạy ⚠️
- `DBManager.init_all()` gọi `MySQLManager.init()` không có try/except bao ngoài
- Nếu MySQL không chạy → exception propagate ra `lifespan` → app crash khi startup
- **Fix:** Wrap từng `manager.init()` trong try/except bên trong `DBManager.init_all()`

### Bug #3 — requirements.txt / requirements.in UTF-16LE ⚠️
- Cả 2 file lưu dạng UTF-16 with BOM → `pip install -r requirements.txt` fail
- **Fix:** Mở file trong editor, Save As → Encoding: UTF-8 (without BOM)

### Bug #4 — Model ID `claude-haiku-4-5-20251001` cần xác minh ⚠️
- `ANTHROPIC_MODEL_FAST = "claude-haiku-4-5-20251001"` trong `core/config.py`
- Model ID này cần được verify với Anthropic API — nếu sai sẽ gây 404 cho KR Agent và Psych Agent
- **Fix:** Kiểm tra `/v1/models` endpoint hoặc tài liệu Anthropic để lấy ID chính xác

### Bug #5 — `common/` và `controller/` rỗng
- Chỉ chứa `__pycache__`, không có source file nào
- Đây là scaffolding thừa từ project generator — không gây lỗi nhưng nên xóa

### Bug #6 — `entity/__init__.py` cần export `ConversationMessage`
- `ConversationRepository` import `from entity import ConversationMessage`
- Nếu `entity/__init__.py` không export đủ → ImportError trong async background task (silent fail)
- **Fix:** Kiểm tra `entity/__init__.py` có `from .conversation_message import ConversationMessage`

### Bug #7 — `psycopg2` cần build tools trên Windows ⚠️
- `requirements.txt` pin `psycopg2==2.9.12` (không phải `psycopg2-binary`)
- Trên Windows không có PostgreSQL dev tools → compilation fail
- **Fix:** Đổi thành `psycopg2-binary==2.9.12` trong requirements

### Bug #8 — `.env` có thể đã commit vào git ⚠️🔴 SECURITY
- File `.env` chứa `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `TELEGRAM_BOT_TOKEN`, Facebook access token, HF token
- Nếu đã commit → **rotate tất cả API keys ngay lập tức**
- **Fix:** Thêm `.env` vào `.gitignore`, dùng `git rm --cached .env`

---

## 10. Checklist Để Chạy Lần Đầu

```
[ ] 1. Re-encode requirements.txt và requirements.in sang UTF-8
[ ] 2. pip install -r requirements.txt  (trong .venv)
[ ] 3. Copy .env.example → .env và điền API keys
[ ] 4. Khởi động PostgreSQL (local hoặc Docker)
[ ] 5. Thêm Base.metadata.create_all(engine) vào PostgresManager.init()
         HOẶC chạy database.sql trên MySQL nếu dùng MySQL
[ ] 6. Viết & chạy ingestion script để populate ChromaDB:
         - Đọc 12 sản phẩm từ seed data / PostgreSQL
         - Chunk theo 3 granularity (overview/specs/reviews)
         - Upsert vào 3 ChromaDB collections
[ ] 7. python main.py (uvicorn sẽ start trên port mặc định)
[ ] 8. Test: POST /api/v1/chat/ với payload {message: "tôi muốn mua vòng tay phong thủy"}
[ ] 9. Kiểm tra SSE stream hoạt động: GET /api/v1/chat/stream
```

---

## 11. Files Tham Chiếu Quan Trọng

| File | Nội dung |
|---|---|
| `agents/orchestrator.py` | Logic routing chính của graph |
| `agents/kr_agent.py` | Hybrid search + ChromaDB query |
| `graph/state.py` | Toàn bộ state schema |
| `core/config.py` | Tất cả env vars + defaults |
| `constants/constants.py` | Magic numbers (MAX_ITERATIONS, lambda weights...) |
| `resources/data/entity_graph.json` | 19-node feng shui entity graph |
| `resources/prompt/orchestrator_agent.md` | System prompt Orchestrator |
| `resources/prompt/synth_agent.md` | System prompt Synth Agent (AIDA) |
| `database.sql` | MySQL DDL schema đầy đủ |
| `resources/migrate/seed.sql` | Mock data đầy đủ (18 bảng) |
| `documents/tai_lieu_ky_thuat_vi.md` | Tài liệu kỹ thuật tiếng Việt (15 phần) |
| `data/checkpoints.db` | LangGraph checkpoint SQLite (đã có sẵn) |

---

*File này được tạo tự động bằng cách scan toàn bộ codebase. Cập nhật lại khi có thay đổi cấu trúc lớn.*
