from sqlalchemy import Column, BigInteger, String, Text, Boolean, Integer, DateTime, ForeignKey, Index, TINYINT

from models.base_model import Base, TimestampMixin


class ProductReview(Base, TimestampMixin):
    """Product reviews with embeddings tracking"""
    __tablename__ = 'ProductReviews'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    product_id = Column(BigInteger, ForeignKey('Products.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(BigInteger, ForeignKey('Users.id', ondelete='SET NULL'))
    order_item_id = Column(BigInteger, ForeignKey('OrderItems.id'))
    
    rating = Column(TINYINT, nullable=False)
    title = Column(String(255))
    body = Column(Text)
    is_verified_purchase = Column(Boolean, default=False)
    is_published = Column(Boolean, default=False, index=True)
    moderated_at = Column(DateTime(6))
    embedding_status = Column(String(50), default='pending', index=True)  # pending, indexed, failed
    
    __table_args__ = (
        Index('idx_review_product', 'product_id'),
        Index('idx_review_user', 'user_id'),
        Index('idx_review_published', 'is_published'),
        Index('idx_review_embedding', 'embedding_status'),
    )

