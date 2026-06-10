# Session Summary — Database & Infrastructure Refactor
**Date:** 2026-06-10  
**Topic:** Chuẩn hoá kết nối database vật lý + ChromaDB trong thư mục `database/`  
**Working dir:** `D:\project\learning\thesis`

---

## 1. Phạm vi thay đổi

| File | Loại | Mô tả |
|------|------|-------|
| `infrastructure/redis_client.py` | Có sẵn | Connection pool Redis (shared, `max_connections=10`) |
| `graph/graph.py` | Sửa | Dùng `redis_client` từ infrastructure thay vì tự build URL |
| `database/__init__.py` | Tạo mới | Package entry-point — `get_db()` cho MySQL |
| `database/database.py` | Sửa | Fix `get_db_session`, xóa `load_dotenv`, xóa `db_manager` thừa |
| `database/mysql_manager.py` | Sửa | Fix import path + fix `get_db()` generator pattern |
| `database/postgres_manager.py` | Sửa | Thay hardcode credentials → `settings.PG_*` |
| `database/vector_db_manager.py` | Viết lại | Multi-collection, OpenAI embeddings, nhất quán với retrieval |
| `core/config.py` | Sửa | Thêm 7 Postgres settings (`PG_HOST`, `PG_PORT`, ...) |

---

## 2. Redis — `graph/graph.py`

### Trước
```python
from core.config import settings

def _build_redis_checkpointer() -> RedisSaver:
    redis_url = (
        f"redis://:{settings.REDIS_PASSWORD}@{settings.REDIS_HOST}:{settings.REDIS_PORT}/0"
        if settings.REDIS_PASSWORD
        else f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0"
    )
    return RedisSaver.from_conn_string(redis_url)
```

### Sau
```python
from infrastructure.redis_client import redis_client

def _build_redis_checkpointer() -> RedisSaver:
    saver = RedisSaver(conn=redis_client)
    saver.setup()   # tạo Redis indexes cho checkpoint storage
    return saver
```

**Lý do:** Tái sử dụng connection pool đã cấu hình sẵn (`max_connections=10`, `socket_timeout=5`, `retry_on_timeout=True`) thay vì tạo kết nối riêng. `saver.setup()` bắt buộc khi dùng constructor trực tiếp (không qua context manager `from_conn_string`).

---

## 3. Vấn đề gốc rễ — `database/` không phải Python package

**Tình trạng trước:** `database/` thiếu `__init__.py` → Python không nhận là package → `from database import DBManager` trong submodule thực ra import root `database.py` (không có `DBManager`/`DatabaseSettings`) → **ImportError** khi chạy.

**Giải pháp:** Tạo `database/__init__.py` chứa MySQL connection setup. Python ưu tiên package hơn module cùng tên, nên `from database import get_db` trong `chat_controller.py` vẫn hoạt động đúng.

```
database/
├── __init__.py          ← NEW: get_db(), engine, SessionLocal (MySQL)
├── database.py          ← DBManager, DatabaseSettings base class
├── mysql_manager.py     ← MySQLConfig + MySQLManager
├── postgres_manager.py  ← PostgresConfig + PostgresManager
└── vector_db_manager.py ← VectorDBManager (3 ChromaDB collections)
```

---

## 4. `database/database.py` — Fix `get_db_session`

### Trước (broken)
```python
@classmethod
def get_db_session(cls, db_key: str = "default") -> Session:
    # yield bên trong @classmethod không có @contextmanager → không hoạt động
    session = cls._session_factories[db_key]()
    try:
        yield session
    finally:
        session.close()
```

### Sau
```python
@classmethod
@contextmanager
def get_db_session(cls, db_key: str = "default") -> Session:
    session = cls._session_factories[db_key]()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

Cũng xóa: `load_dotenv()` (đã có trong `main.py`) và `db_manager = DBManager()` (vô nghĩa vì mọi method là `@classmethod`).

---

## 5. `database/mysql_manager.py` — Fix import + generator

```python
# Import cũ (sai — root database.py không có DBManager)
from database import DatabaseSettings, DBManager

# Import mới (đúng — dùng full package path)
from database.database import DatabaseSettings, DBManager

# get_db() cũ (sai pattern)
def get_db():
    db_gen = DBManager.get_db_session("mysql")
    yield next(db_gen)   # context manager không có next()

# get_db() mới (đúng — FastAPI dependency pattern)
def get_db():
    with DBManager.get_db_session("mysql") as session:
        yield session
```

---

## 6. `database/postgres_manager.py` — Thay hardcode bằng settings

Thêm vào `core/config.py`:
```python
PG_HOST: str = "localhost"
PG_PORT: int = 5432
PG_NAME: str = "ai-chatbot"
PG_USER: str = "admin"
PG_PASSWORD: str = "123456789"
PG_POOL_SIZE: int = 10
PG_MAX_OVERFLOW: int = 20
```

Postgres manager đổi từ hardcode sang `settings.PG_*`, đồng nhất pattern `get_db()` với MySQL.

---

## 7. `database/vector_db_manager.py` — Rewrite hoàn toàn

### Vấn đề trước
| Lỗi | Chi tiết |
|-----|---------|
| `settings.EMBEDDING_MODEL_NAME` | Không tồn tại trong `core/config.py` → `AttributeError` |
| `settings.COLLECTION_NAME` | Không tồn tại → `AttributeError` |
| `SentenceTransformerEmbeddingFunction` | Project dùng OpenAI `text-embedding-3-small`, không phải SentenceTransformer |
| Single-collection | Project có 3 collection: `product_overview`, `product_specs`, `product_reviews` |
| `DEBUG_PATH_ACTUAL` print | Leftover debug code |

### Thiết kế sau — nhất quán với retrieval pipeline

```
hybrid_search.py
    └── query_embeddings=[embed_query(text)]    ← pre-computed OpenAI vector
    └── chromadb_client.get_all_collections()   ← 3 collections, no embedding_fn

vector_db_manager.py (ingestion)
    └── _embed(documents) → embed_documents()   ← same OpenAI model
    └── collection.add(embeddings=vecs, ...)    ← pre-computed, nhất quán
```

- Không đặt `embedding_function` trong collection → tránh conflict với `retrieval/chromadb_client.py`
- Lazy import `retrieval.embeddings` trong method → tránh circular import
- CRUD methods nhận thêm `embeddings: list = None` — nếu caller đã tự embed thì truyền vào, không cần gọi OpenAI lại

---

## 8. Sơ đồ kết nối sau refactor

```
main.py (FastAPI lifespan)
    └── get_compiled_graph()
            └── RedisSaver(conn=redis_client)   ← infrastructure/redis_client.py
                    └── ConnectionPool(host, port, password, max_connections=10)

chat_controller.py
    └── from database import get_db             ← database/__init__.py
            └── MySQL engine (pymysql, utf8mb4, pool_size=10)

hybrid_search.py  (agents → KR Agent)
    └── retrieval/chromadb_client.py
            └── chromadb.PersistentClient(CHROMA_PATH)
                    └── 3 collections (cosine HNSW)
    └── retrieval/embeddings.py
            └── OpenAIEmbeddings(text-embedding-3-small, 1536 dims)

database/vector_db_manager.py  (data ingestion scripts)
    └── chromadb.PersistentClient(CHROMA_PATH)   ← cùng path với retrieval
    └── retrieval/embeddings.embed_documents()   ← cùng model với retrieval
```

---

## 9. Lưu ý khi triển khai

- Root `database.py` hiện bị **shadowed** bởi `database/` package — có thể xóa an toàn để tránh nhầm lẫn.
- `PostgresManager` được đăng ký vào `DBManager._registered_managers` nhưng `DBManager.init_all()` chưa được gọi từ `main.py` → Postgres chưa được kích hoạt. Chỉ cần khi dự án mở rộng sang dùng PostgreSQL.
- `RedisSaver.setup()` an toàn để gọi nhiều lần (idempotent) — tạo indexes nếu chưa có, bỏ qua nếu đã có.
- `vector_db_manager.py` dùng lazy import `retrieval.embeddings` để tránh circular import (`retrieval` → `common.constants` → không import `database`, nhưng an toàn hơn khi để lazy).
