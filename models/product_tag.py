from sqlalchemy import Column, BigInteger, ForeignKey

from models.base_model import Base


class ProductTag(Base):
    """M:N junction between Products and Tags"""
    __tablename__ = 'ProductTags'
    
    product_id = Column(BigInteger, ForeignKey('Products.id', ondelete='CASCADE'), primary_key=True)
    tag_id = Column(BigInteger, ForeignKey('Tags.id', ondelete='CASCADE'), primary_key=True)

