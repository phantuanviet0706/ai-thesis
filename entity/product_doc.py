from typing import Any, Optional
from pydantic import BaseModel, Field


class ProductDoc(BaseModel):
    """Pydantic model for a product document retrieved from ChromaDB."""
    id: str
    name: str
    sku: Optional[str] = None
    short_description: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    brand: Optional[str] = None
    unit_price: float
    sale_price: Optional[float] = None
    in_stock: bool = True
    attributes: Optional[dict[str, Any]] = None
    collection_source: str = Field(description="Which ChromaDB collection this came from")
    chunk_text: str = Field(description="The raw chunk text that was retrieved")
    composite_score: float = Field(default=0.0, description="Final hybrid search score")
