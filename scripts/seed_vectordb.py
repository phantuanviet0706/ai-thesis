"""
seed_vectordb.py — Đồng bộ dữ liệu từ MySQL vào ChromaDB cho KR Agent.

Chiến lược 3 collection (thesis §3.2.2):
  product_overview : tóm tắt ngắn (tên, giá, danh mục) — cho truy vấn chung
  product_specs    : mô tả đầy đủ + thuộc tính kỹ thuật — cho truy vấn chi tiết
  product_reviews  : mỗi review 1 chunk — cho truy vấn trải nghiệm / đánh giá

Usage:
  python scripts/seed_vectordb.py            # chỉ index các bản ghi pending
  python scripts/seed_vectordb.py --force    # re-index toàn bộ
  python scripts/seed_vectordb.py --stats    # chỉ xem thống kê ChromaDB
"""

import json
import sys
from pathlib import Path

# Thêm thư mục gốc vào sys.path để import các module dự án
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from constants.constants import COLLECTION_OVERVIEW, COLLECTION_SPECS, COLLECTION_REVIEWS
from database import get_db
from database.vector_db_manager import VectorDBManager
from entity.brand import Brand
from entity.category import Category
from entity.product import Product
from entity.product_review import ProductReview
from retrieval.embeddings import embed_documents

BATCH_SIZE = 50


# ---------------------------------------------------------------------------
# Text builders
# ---------------------------------------------------------------------------

def _build_overview_text(p: Product, category: str, brand: str) -> str:
    price = f"{float(p.unit_price):,.0f}₫"
    if p.sale_price and float(p.sale_price) < float(p.unit_price):
        price = f"{float(p.unit_price):,.0f}₫ → {float(p.sale_price):,.0f}₫ (giảm giá)"

    lines = [
        f"Tên sản phẩm: {p.name}",
        f"SKU: {p.sku}" if p.sku else None,
        f"Danh mục: {category}" if category else None,
        f"Thương hiệu: {brand}" if brand else None,
        f"Giá: {price}",
        f"Tình trạng: {'Còn hàng' if p.in_stock else 'Hết hàng'}",
        f"Mô tả ngắn: {p.short_description}" if p.short_description else None,
    ]
    return "\n".join(line for line in lines if line)


def _build_specs_text(p: Product, category: str, brand: str) -> str:
    price = f"{float(p.unit_price):,.0f}₫"
    if p.sale_price and float(p.sale_price) < float(p.unit_price):
        price = f"{float(p.unit_price):,.0f}₫ → {float(p.sale_price):,.0f}₫ (giảm giá)"

    attrs_str = ""
    if p.attributes and isinstance(p.attributes, dict):
        attrs_str = "\n".join(f"  - {k}: {v}" for k, v in p.attributes.items())

    lines = [
        f"Tên sản phẩm: {p.name}",
        f"SKU: {p.sku}" if p.sku else None,
        f"Danh mục: {category}" if category else None,
        f"Thương hiệu: {brand}" if brand else None,
        f"Giá: {price} | Tồn kho: {p.stock_qty} sản phẩm",
        f"Mô tả đầy đủ: {p.description}" if p.description else None,
        f"Thuộc tính kỹ thuật:\n{attrs_str}" if attrs_str else None,
    ]
    return "\n".join(line for line in lines if line)


def _build_review_text(review: ProductReview, product_name: str, category: str) -> str:
    sentiment = "Tích cực" if review.rating else "Tiêu cực"
    verified = "Đã xác thực mua hàng" if review.is_verified_purchase else "Chưa xác thực"

    lines = [
        f"Sản phẩm: {product_name}",
        f"Danh mục: {category}" if category else None,
        f"Đánh giá: {sentiment} | {verified}",
        f"Tiêu đề: {review.title}" if review.title else None,
        f"Nội dung: {review.body}" if review.body else None,
    ]
    return "\n".join(line for line in lines if line)


# ---------------------------------------------------------------------------
# Metadata builders
# ---------------------------------------------------------------------------

def _product_meta(p: Product, category: str, brand: str) -> dict:
    return {
        "product_id": str(p.id),
        "name": p.name or "",
        "sku": p.sku or "",
        "short_description": p.short_description or "",
        "description": (p.description or "")[:500],
        "category": category,
        "brand": brand,
        "unit_price": float(p.unit_price),
        "sale_price": float(p.sale_price) if p.sale_price else 0.0,
        "in_stock": bool(p.in_stock),
        "attributes": json.dumps(p.attributes, ensure_ascii=False) if p.attributes else "",
    }


def _review_meta(review: ProductReview, p: Product, category: str) -> dict:
    return {
        "product_id": str(p.id),
        "name": p.name or "",
        "sku": p.sku or "",
        "short_description": p.short_description or "",
        "description": (p.description or "")[:500],
        "category": category,
        "brand": "",
        "unit_price": float(p.unit_price),
        "sale_price": float(p.sale_price) if p.sale_price else 0.0,
        "in_stock": bool(p.in_stock),
        "attributes": json.dumps(p.attributes, ensure_ascii=False) if p.attributes else "",
        "review_id": str(review.id),
        "rating": int(bool(review.rating)),
        "is_verified": bool(review.is_verified_purchase),
    }


# ---------------------------------------------------------------------------
# Seeding logic
# ---------------------------------------------------------------------------

def seed_products(db: Session, vdb: VectorDBManager, force: bool) -> tuple[int, int]:
    stmt = (
        select(Product, Category, Brand)
        .outerjoin(Category, Product.category_id == Category.id)
        .outerjoin(Brand, Product.brand_id == Brand.id)
        .where(Product.status == "active")
    )
    if not force:
        stmt = stmt.where(Product.embedding_status == "pending")

    rows = db.execute(stmt).fetchall()
    if not rows:
        print("  Không có sản phẩm nào cần index.")
        return 0, 0

    print(f"  Tìm thấy {len(rows)} sản phẩm.")

    overview_col = vdb.get_collection(COLLECTION_OVERVIEW)
    specs_col = vdb.get_collection(COLLECTION_SPECS)
    indexed = failed = 0

    for batch_start in range(0, len(rows), BATCH_SIZE):
        batch = rows[batch_start : batch_start + BATCH_SIZE]

        o_ids, o_docs, o_metas = [], [], []
        s_ids, s_docs, s_metas = [], [], []
        success_ids = []

        for product, category, brand in batch:
            try:
                cat_name = category.name if category else "Pancharm"
                brand_name = brand.name if brand else "Pancharm"
                meta = _product_meta(product, cat_name, brand_name)

                o_ids.append(f"overview_{product.id}")
                o_docs.append(_build_overview_text(product, cat_name, brand_name))
                o_metas.append(meta)

                s_ids.append(f"specs_{product.id}")
                s_docs.append(_build_specs_text(product, cat_name, brand_name))
                s_metas.append(meta)

                success_ids.append(product.id)
            except Exception as exc:
                print(f"  ✗ Sản phẩm #{product.id}: {exc}")
                failed += 1

        if not o_ids:
            continue

        o_vecs = embed_documents(o_docs)
        s_vecs = embed_documents(s_docs)

        overview_col.upsert(ids=o_ids, documents=o_docs, embeddings=o_vecs, metadatas=o_metas)
        specs_col.upsert(ids=s_ids, documents=s_docs, embeddings=s_vecs, metadatas=s_metas)

        db.execute(
            update(Product)
            .where(Product.id.in_(success_ids))
            .values(embedding_status="indexed")
        )
        db.commit()

        batch_num = batch_start // BATCH_SIZE + 1
        print(f"  Batch {batch_num}: {len(success_ids)} sản phẩm ✓")
        indexed += len(success_ids)

    return indexed, failed


def seed_reviews(db: Session, vdb: VectorDBManager, force: bool) -> tuple[int, int]:
    stmt = (
        select(ProductReview, Product, Category)
        .join(Product, ProductReview.product_id == Product.id)
        .outerjoin(Category, Product.category_id == Category.id)
        .where(
            ProductReview.is_published == True,
            ProductReview.body.isnot(None),
        )
    )
    if not force:
        stmt = stmt.where(ProductReview.embedding_status == "pending")

    rows = db.execute(stmt).fetchall()
    if not rows:
        print("  Không có review nào cần index.")
        return 0, 0

    print(f"  Tìm thấy {len(rows)} review.")

    review_col = vdb.get_collection(COLLECTION_REVIEWS)
    indexed = failed = 0

    for batch_start in range(0, len(rows), BATCH_SIZE):
        batch = rows[batch_start : batch_start + BATCH_SIZE]

        r_ids, r_docs, r_metas = [], [], []
        success_ids = []

        for review, product, category in batch:
            try:
                cat_name = category.name if category else ""
                r_ids.append(f"review_{review.id}")
                r_docs.append(_build_review_text(review, product.name, cat_name))
                r_metas.append(_review_meta(review, product, cat_name))
                success_ids.append(review.id)
            except Exception as exc:
                print(f"  ✗ Review #{review.id}: {exc}")
                failed += 1

        if not r_ids:
            continue

        r_vecs = embed_documents(r_docs)
        review_col.upsert(ids=r_ids, documents=r_docs, embeddings=r_vecs, metadatas=r_metas)

        db.execute(
            update(ProductReview)
            .where(ProductReview.id.in_(success_ids))
            .values(embedding_status="indexed")
        )
        db.commit()

        batch_num = batch_start // BATCH_SIZE + 1
        print(f"  Batch {batch_num}: {len(success_ids)} review ✓")
        indexed += len(success_ids)

    return indexed, failed


def print_stats(vdb: VectorDBManager) -> None:
    print("\nChromaDB stats:")
    total = 0
    for col_name in [COLLECTION_OVERVIEW, COLLECTION_SPECS, COLLECTION_REVIEWS]:
        count = vdb.get_collection(col_name).count()
        total += count
        print(f"  {col_name:<30} {count:>5} documents")
    print(f"  {'TOTAL':<30} {total:>5} documents")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    args = sys.argv[1:]
    force = "--force" in args
    stats_only = "--stats" in args

    vdb = VectorDBManager()

    if stats_only:
        print_stats(vdb)
        return

    if force:
        print("Force mode: re-index toàn bộ sản phẩm và review\n")
    else:
        print("Incremental mode: chỉ index các bản ghi pending\n")
        print("  (Dùng --force để re-index toàn bộ)\n")

    print("[1/2] Indexing sản phẩm → product_overview + product_specs ...")
    with get_db() as db:
        prod_ok, prod_fail = seed_products(db, vdb, force)

    print(f"\n[2/2] Indexing reviews → product_reviews ...")
    with get_db() as db:
        rev_ok, rev_fail = seed_reviews(db, vdb, force)

    print(f"\nKết quả:")
    print(f"  Sản phẩm : {prod_ok} thành công, {prod_fail} thất bại")
    print(f"  Reviews  : {rev_ok} thành công, {rev_fail} thất bại")

    print_stats(vdb)


if __name__ == "__main__":
    main()
