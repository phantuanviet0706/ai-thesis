import asyncio
from contextlib import contextmanager
from typing import Any, Generator, TypeVar
from urllib.parse import quote_plus

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from core.config import settings

T = TypeVar("T")

# MySQL error codes đáng để retry — đều là lỗi THOÁNG QUA (transaction xung đột đã tự giải
# quyết ngay sau đó), không phải lỗi logic:
#   1213 = Deadlock found when trying to get lock
#   1205 = Lock wait timeout exceeded
_TRANSIENT_LOCK_ERRNOS = (1213, 1205)

# quote_plus bắt buộc — user/password chứa ký tự đặc biệt (vd "abc@123") sẽ phá vỡ URL nếu
# ghép thô: "@" thứ 2 bị hiểu nhầm thành phần phân cách userinfo/host, kết nối sai host/port.
DATABASE_URL = (
    f"mysql+pymysql://{quote_plus(settings.DB_USER)}:{quote_plus(settings.DB_PASSWORD)}"
    f"@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
    f"?charset=utf8mb4"
)

engine = create_engine(
    DATABASE_URL,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_pre_ping=True,
    echo=False,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


@contextmanager
def get_db() -> Generator[Session, Any, None]:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db() -> None:
    """Tạo tất cả bảng từ ORM models nếu chưa tồn tại."""
    from entity.base_model import Base
    import entity  # noqa: F401 — đăng ký tất cả ORM models với Base metadata
    Base.metadata.create_all(bind=engine)


def is_transient_lock_error(exc: BaseException) -> bool:
    """
    @desc Kiểm tra xem exception có phải deadlock/lock-wait-timeout thoáng qua của MySQL không
    (SQLAlchemy bọc lỗi gốc pymysql trong .orig). Các lỗi này nên retry vì giao dịch xung đột
    thường đã hoàn tất ngay khi lỗi được ném ra — retry lại gần như luôn thành công ngay lần đầu.
    @params exc (BaseException): Exception bắt được từ 1 lệnh DB
    @return bool: True nếu là lỗi nên retry
    """
    orig = getattr(exc, "orig", exc)
    args = getattr(orig, "args", None)
    return bool(args) and args[0] in _TRANSIENT_LOCK_ERRNOS


async def run_with_deadlock_retry(fn, *args, max_attempts: int = 3, **kwargs) -> T:
    """
    @desc Chạy 1 hàm đồng bộ (1 transaction DB) trong thread pool, tự động retry tối đa
    max_attempts lần nếu gặp deadlock/lock wait timeout thoáng qua. Dùng cho các background
    task ghi cùng bảng với task khác đang chạy song song (vd ChatService._persist_turn và
    BusinessService._process_turn_sync cùng update ConversationSessions của 1 session).
    @params fn: Hàm đồng bộ cần chạy (thường là 1 method mở transaction qua get_db())
    @params args: Tham số vị trí truyền cho fn
    @params max_attempts (int): Số lần thử tối đa, mặc định 3
    @params kwargs: Tham số từ khóa truyền cho fn
    @return T: Giá trị trả về của fn nếu thành công
    """
    for attempt in range(1, max_attempts + 1):
        try:
            return await asyncio.to_thread(fn, *args, **kwargs)
        except Exception as exc:
            if attempt < max_attempts and is_transient_lock_error(exc):
                await asyncio.sleep(0.05 * attempt)
                continue
            raise
