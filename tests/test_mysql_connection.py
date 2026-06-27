"""
Test kết nối MySQL — chạy độc lập, không cần pytest.
Usage: python tests/test_mysql_connection.py
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from core.config import settings

# ── Màu terminal ──────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def ok(msg):   print(f"  {GREEN}✔{RESET}  {msg}")
def fail(msg): print(f"  {RED}✘{RESET}  {msg}")
def info(msg): print(f"  {CYAN}→{RESET}  {msg}")
def warn(msg): print(f"  {YELLOW}⚠{RESET}  {msg}")
def header(msg): print(f"\n{BOLD}{msg}{RESET}")

# ── Config hiển thị ───────────────────────────────────────────────────────────
def print_config():
    header("── Cấu hình MySQL (từ .env / config.py) ──")
    info(f"Host     : {settings.DB_HOST}")
    info(f"Port     : {settings.DB_PORT}")
    info(f"Database : {settings.DB_NAME}")
    info(f"User     : {settings.DB_USER}")
    info(f"Password : {'*' * len(settings.DB_PASSWORD)}")

# ── Test 1: PyMySQL trực tiếp ─────────────────────────────────────────────────
def test_pymysql_direct():
    header("── Test 1: Kết nối trực tiếp qua PyMySQL ──")
    try:
        import pymysql
    except ImportError:
        fail("PyMySQL chưa được cài — chạy: pip install PyMySQL")
        return False

    try:
        t0 = time.monotonic()
        conn = pymysql.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database=settings.DB_NAME,
            charset="utf8mb4",
            connect_timeout=5,
        )
        latency = (time.monotonic() - t0) * 1000
        ok(f"Kết nối thành công ({latency:.1f} ms)")

        with conn.cursor() as cur:
            cur.execute("SELECT VERSION()")
            version = cur.fetchone()[0]
            ok(f"MySQL version: {version}")

            cur.execute("SELECT DATABASE()")
            db = cur.fetchone()[0]
            ok(f"Database đang dùng: {db}")

        conn.close()
        return True
    except Exception as e:
        fail(f"Kết nối thất bại: {e}")
        return False

# ── Test 2: SQLAlchemy engine ─────────────────────────────────────────────────
def test_sqlalchemy_engine():
    header("── Test 2: Kết nối qua SQLAlchemy engine ──")
    try:
        from sqlalchemy import create_engine, text

        url = (
            f"mysql+pymysql://{settings.DB_USER}:{settings.DB_PASSWORD}"
            f"@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
            f"?charset=utf8mb4"
        )
        engine = create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 5})

        t0 = time.monotonic()
        with engine.connect() as conn:
            latency = (time.monotonic() - t0) * 1000
            ok(f"Engine kết nối thành công ({latency:.1f} ms)")

            result = conn.execute(text("SELECT VERSION()")).scalar()
            ok(f"MySQL version: {result}")

        engine.dispose()
        return True
    except Exception as e:
        fail(f"SQLAlchemy engine thất bại: {e}")
        return False

# ── Test 3: Liệt kê bảng trong DB ────────────────────────────────────────────
def test_list_tables():
    header("── Test 3: Liệt kê bảng trong database ──")
    try:
        import pymysql
        conn = pymysql.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database=settings.DB_NAME,
            charset="utf8mb4",
            connect_timeout=5,
        )
        with conn.cursor() as cur:
            cur.execute("SHOW TABLES")
            tables = [row[0] for row in cur.fetchall()]

        conn.close()

        if tables:
            ok(f"Tìm thấy {len(tables)} bảng:")
            for t in tables:
                info(t)
        else:
            warn("Database tồn tại nhưng chưa có bảng nào — cần chạy database.sql")

        return True
    except Exception as e:
        fail(f"Không thể liệt kê bảng: {e}")
        return False

# ── Test 4: Query thử bảng Brands (nếu đã seed) ──────────────────────────────
def test_sample_query():
    header("── Test 4: Query thử bảng Brands (seed data) ──")
    try:
        import pymysql
        conn = pymysql.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database=settings.DB_NAME,
            charset="utf8mb4",
            connect_timeout=5,
        )
        with conn.cursor(pymysql.cursors.DictCursor) as cur:
            cur.execute("SELECT id, name, slug FROM Brands LIMIT 5")
            rows = cur.fetchall()

        conn.close()

        if rows:
            ok(f"Brands ({len(rows)} bản ghi đầu):")
            for r in rows:
                info(f"  [{r['id']}] {r['name']} ({r['slug']})")
        else:
            warn("Bảng Brands rỗng — cần chạy resources/migrate/seed.sql")

        return True
    except Exception as e:
        if "doesn't exist" in str(e):
            warn("Bảng Brands chưa tồn tại — cần chạy database.sql trước")
        else:
            fail(f"Query thất bại: {e}")
        return False

# ── Test 5: DBManager (full stack) ───────────────────────────────────────────
def test_db_manager():
    header("── Test 5: Kết nối qua DBManager (full stack) ──")
    try:
        from database.mysql_manager import MySQLManager
        from database.database import DBManager
        from sqlalchemy import text

        MySQLManager.init()
        with DBManager.get_db_session("mysql") as session:
            result = session.execute(text("SELECT 1 + 1 AS result")).scalar()
            ok(f"DBManager session hoạt động — SELECT 1+1 = {result}")

        return True
    except Exception as e:
        fail(f"DBManager thất bại: {e}")
        return False

# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"\n{BOLD}{'=' * 50}{RESET}")
    print(f"{BOLD}  MYSQL CONNECTION TEST — Pancharm MAS{RESET}")
    print(f"{BOLD}{'=' * 50}{RESET}")

    print_config()

    results = {
        "PyMySQL trực tiếp"      : test_pymysql_direct(),
        "SQLAlchemy engine"      : test_sqlalchemy_engine(),
        "Liệt kê bảng"          : test_list_tables(),
        "Query Brands"           : test_sample_query(),
        "DBManager (full stack)" : test_db_manager(),
    }

    header("── Kết quả tổng hợp ──")
    passed = sum(1 for v in results.values() if v)
    total  = len(results)
    for name, status in results.items():
        symbol = f"{GREEN}PASS{RESET}" if status else f"{RED}FAIL{RESET}"
        print(f"  [{symbol}] {name}")

    print(f"\n  {BOLD}{'Tất cả test pass ✔' if passed == total else f'{passed}/{total} test pass'}{RESET}\n")
    sys.exit(0 if passed == total else 1)
