from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator, ConfigDict

from constants.error_code import ErrorCode
from exceptions.app_exception import AppException

class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)


class BaseListSchema(BaseModel):
    offset: int = Field(0, ge=0, description='Vị trí bắt đầu lấy bản ghi')
    limit: int = Field(50, ge=0, le=200, description="Số lượng bản ghi tối đa mỗi trang")
    created_at_from: Optional[datetime] = None
    created_at_to: Optional[datetime] = None
    query: Optional[str] = Field(None, min_length=2, description="Từ khóa tìm kiếm")

    @model_validator(mode="after")
    def validate_common_logic(self) -> 'BaseListSchema':
        """Validate filter khoảng ngày tạo"""
        if self.created_at_from and self.created_at_to:
            if self.created_at_from > self.created_at_to:
                raise AppException(ErrorCode.COMMON_VALIDATOR_DATE)
        return self