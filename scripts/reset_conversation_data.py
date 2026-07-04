"""
reset_conversation_data.py — Xóa toàn bộ dữ liệu hội thoại/checkpoint để test lại từ đầu.

QUAN TRỌNG: Dừng server (uvicorn/main.py) trước khi chạy script này.
Nếu server đang chạy, checkpointer (Redis hoặc AsyncSQLite) vẫn giữ session cũ
trong bộ nhớ/kết nối và sẽ tiếp tục "nhớ" hội thoại trước đó dù bạn xóa dữ liệu.

Reset gồm 4 nguồn (mỗi nguồn có thể tắt riêng bằng flag):
  1. MySQL   — ConversationSessions, ConversationMessages, PsychStateLogs,
               AgentPerformanceLogs, Orders/OrderItems/Payments, Carts/CartItems,
               AuditLogs, Users/UserProfiles/UserAddresses
               (KHÔNG đụng: Products, Brands, Categories, Tags, SystemConfigs — catalog)
  2. Redis   — FLUSHDB toàn bộ (chứa LangGraph RedisSaver checkpoints + rate-limit counters)
  3. SQLite  — data/checkpoints.db, .db-shm, .db-wal (AsyncSqliteSaver fallback)
  4. ChromaDB— 3 collection training_* (không đụng product_overview/specs/reviews)

Usage:
  python scripts/reset_conversation_data.py            # xác nhận rồi reset tất cả
  python scripts/reset_conversation_data.py --yes       # bỏ qua xác nhận
  python scripts/reset_conversation_data.py --keep-users    # giữ Users/UserProfiles/UserAddresses
  python scripts/reset_conversation_data.py --keep-redis    # không đụng Redis
  python scripts/reset_conversation_data.py --keep-chroma   # không đụng ChromaDB training data
  python scripts/reset_conversation_data.py --keep-sqlite   # không đụng file checkpoints.db
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import text

from core.config import settings
from database import engine, get_db

# Bảng thuộc về dữ liệu hội thoại/nghiệp vụ phát sinh khi chat — sẽ bị xóa.
# Thứ tự không quan trọng vì FOREIGN_KEY_CHECKS được    tắt tạm thời.
CONVERSATION_TABLES = [
    "AgentPerformanceLogs",
    "PsychStateLogs",
    "ConversationMessages",
    "ConversationSessions",
    "OrderItems",
    "Payments",
    "Orders",
    "CartItems",
    "Carts",
    "AuditLogs",
]

# Bảng liên quan đến định danh khách hàng — chỉ xóa nếu không có --keep-users
USER_TABLES = [
    "UserAddresses",
    "UserProfiles",
    "Users",
]

TRAINING_COLLECTIONS = [
    "training_conversations",
    "training_psych_labels",
    "training_sessions_success",
]


def reset_mysql(keep_users: bool) -> None:
    tables = CONVERSATION_TABLES + ([] if keep_users else USER_TABLES)
    with get_db() as db:
        db.execute(text("SET FOREIGN_KEY_CHECKS=0"))
        for table in tables:
            db.execute(text(f"TRUNCATE TABLE `{table}`"))
            print(f"  [MySQL] TRUNCATE {table}")
        db.execute(text("SET FOREIGN_KEY_CHECKS=1"))
    print("[MySQL] Done.")


def reset_redis() -> None:
    from infrastructure.redis_client import redis_client
    try:
        redis_client.flushdb()
        print(f"[Redis] FLUSHDB done ({settings.REDIS_HOST}:{settings.REDIS_PORT}) — "
              f"đã xóa cả LangGraph checkpoints lẫn rate-limit counters.")
    except Exception as exc:
        print(f"[Redis] Bỏ qua (không kết nối được hoặc không dùng Redis): {exc}")


def reset_sqlite_checkpoints() -> None:
    db_dir = Path("data")
    for suffix in ("checkpoints.db", "checkpoints.db-shm", "checkpoints.db-wal"):
        path = db_dir / suffix
        if not path.exists():
            continue
        try:
            path.unlink()
            print(f"  [SQLite] Deleted {path}")
        except PermissionError:
            print(
                f"  [SQLite] KHÔNG xóa được {path} (đang bị giữ bởi tiến trình khác). "
                f"Hãy dừng server rồi chạy lại script."
            )
    print("[SQLite] Done.")


def reset_chroma_training_collections() -> None:
    from database.vector_db_manager import VectorDBManager
    vdb = VectorDBManager()
    for name in TRAINING_COLLECTIONS:
        try:
            vdb.client.delete_collection(name=name)
            print(f"  [Chroma] Deleted collection '{name}'")
        except Exception as exc:
            print(f"  [Chroma] Bỏ qua '{name}' (có thể chưa tồn tại): {exc}")
    print("[Chroma] Done. (Catalog: product_overview/specs/reviews giữ nguyên)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--yes", action="store_true", help="Bỏ qua xác nhận")
    parser.add_argument("--keep-users", action="store_true", help="Giữ Users/UserProfiles/UserAddresses")
    parser.add_argument("--keep-redis", action="store_true", help="Không đụng Redis")
    parser.add_argument("--keep-sqlite", action="store_true", help="Không đụng data/checkpoints.db")
    parser.add_argument("--keep-chroma", action="store_true", help="Không đụng ChromaDB training_*")
    args = parser.parse_args()

    print(f"MySQL target : {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")
    print(f"Redis target : {settings.REDIS_HOST}:{settings.REDIS_PORT}")
    print()
    if not args.yes:
        confirm = input(
            "Thao tác này sẽ XÓA VĨNH VIỄN toàn bộ lịch sử hội thoại/checkpoint/đơn hàng test. "
            "Đã dừng server chưa và chắc chắn muốn tiếp tục? (gõ 'yes' để xác nhận): "
        )
        if confirm.strip().lower() != "yes":
            print("Đã hủy.")
            return

    print("\n== Reset MySQL ==")
    reset_mysql(keep_users=args.keep_users)

    if not args.keep_redis:
        print("\n== Reset Redis ==")
        reset_redis()

    if not args.keep_sqlite:
        print("\n== Reset SQLite checkpoint ==")
        reset_sqlite_checkpoints()

    if not args.keep_chroma:
        print("\n== Reset ChromaDB training collections ==")
        reset_chroma_training_collections()

    print("\nHoàn tất. Khởi động lại server (main.py) trước khi test lại từ đầu.")


if __name__ == "__main__":
    main()
