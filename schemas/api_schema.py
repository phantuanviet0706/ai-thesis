from typing import TypeVar, Generic, Optional

from pydantic import BaseModel

T = TypeVar('T')

class ApiResponse(BaseModel, Generic[T]):
    code: int
    message: str
    result: Optional[T] = None
