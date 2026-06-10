from sqlalchemy import Column, BigInteger, String, Text, Boolean, Integer, ForeignKey, JSON, Index, DECIMAL

from entity.base_model import Base, TimestampMixin


class Product(Base, TimestampMixin):
    """Product entity with embeddings tracking for KR Agent"""
    __tablename__ = 'Products'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), nullable=False, unique=True)
    sku = Column(String(100), unique=True)
    description = Column(Text)
    short_description = Column(String(500))
    category_id = Column(BigInteger, ForeignKey('Categories.id', ondelete='SET NULL'))
    brand_id = Column(BigInteger, ForeignKey('Brands.id', ondelete='SET NULL'))

    unit_price = Column(DECIMAL(10, 2), nullable=False)
    sale_price = Column(DECIMAL(10, 2))
    in_stock = Column(Boolean, default=True, index=True)
    stock_qty = Column(Integer, default=0, nullable=False)

    attributes = Column(JSON)
    status = Column(String(50), nullable=False)  # draft, active, inactive, archived
    embedding_status = Column(String(50), nullable=False, default='pending')  # pending, indexed, failed

    __table_args__ = (
        Index('idx_product_id', 'id'),
        Index('idx_product_category', 'category_id'),
        Index('idx_product_brand', 'brand_id'),
        Index('idx_product_status', 'status'),
        Index('idx_product_price', 'unit_price'),
        Index('idx_product_stock', 'in_stock', 'stock_qty'),
        Index('idx_product_embedding', 'embedding_status'),
    )

