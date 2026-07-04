"""
cleanup_chroma_orphans.py — Dọn các thư mục segment mồ côi trong chroma_db/.

BỐI CẢNH: mỗi thư mục UUID trong chroma_db/ tương ứng với 1 VECTOR SEGMENT của 1
collection (không phải "1 folder mỗi lần insert" — insert/upsert chỉ ghi đè file bên
trong 1 folder đã tồn tại của collection đó). Thư mục mồ côi phát sinh khi
VectorDBManager.get_collection() tự phát hiện HNSW metadata cũ không tương thích
(vd đổi embedding model/dims) và gọi delete_collection() + create_collection() —
folder vật lý của segment cũ đôi khi không được ChromaDB dọn sạch, để lại rác.

Script này so khớp:
  - Danh sách segment ID (scope=VECTOR) đang thực sự được tham chiếu trong chroma.sqlite3
  - Danh sách thư mục UUID thực tế nằm trong chroma_db/
rồi xoá các thư mục KHÔNG còn được tham chiếu.

Usage:
  python scripts/cleanup_chroma_orphans.py            # liệt kê orphan, hỏi xác nhận rồi xoá
  python scripts/cleanup_chroma_orphans.py --dry-run  # chỉ liệt kê, không xoá
  python scripts/cleanup_chroma_orphans.py --yes      # xoá luôn, không hỏi xác nhận
"""

import argparse
import shutil
import sqlite3
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

from core.config import settings


def _is_uuid_dir_name(name: str) -> bool:
    try:
        uuid.UUID(name)
        return True
    except ValueError:
        return False


def find_orphans(chroma_path: Path) -> tuple[list[Path], set[str]]:
    """@return (danh sách folder mồ côi, tập segment ID đang được dùng)"""
    db_path = chroma_path / "chroma.sqlite3"
    con = sqlite3.connect(db_path)
    try:
        rows = con.execute("SELECT id FROM segments").fetchall()
    finally:
        con.close()
    live_segment_ids = {r[0] for r in rows}

    orphans = [
        d for d in chroma_path.iterdir()
        if d.is_dir() and _is_uuid_dir_name(d.name) and d.name not in live_segment_ids
    ]
    return orphans, live_segment_ids


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="Chỉ liệt kê, không xoá")
    parser.add_argument("--yes", action="store_true", help="Xoá luôn, không hỏi xác nhận")
    args = parser.parse_args()

    chroma_path = Path(settings.CHROMA_PATH).resolve()
    print(f"ChromaDB path: {chroma_path}")

    orphans, live_ids = find_orphans(chroma_path)

    if not orphans:
        print("Không có thư mục mồ côi nào — chroma_db/ đang sạch.")
        return

    print(f"\nTìm thấy {len(orphans)} thư mục mồ côi (không thuộc segment nào đang active):")
    for o in orphans:
        size_mb = sum(f.stat().st_size for f in o.rglob("*") if f.is_file()) / (1024 * 1024)
        print(f"  - {o.name}  (~{size_mb:.2f} MB)")

    if args.dry_run:
        print("\n(--dry-run: không xoá gì cả)")
        return

    if not args.yes:
        confirm = input("\nXoá toàn bộ thư mục mồ côi trên? (gõ 'yes' để xác nhận): ")
        if confirm.strip().lower() != "yes":
            print("Đã hủy.")
            return

    for o in orphans:
        shutil.rmtree(o)
        print(f"  Deleted {o.name}")
    print("\nHoàn tất.")


if __name__ == "__main__":
    main()
