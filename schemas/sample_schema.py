from typing import Optional

from schemas.base_schema import BaseSchema, BaseListSchema


class SampleSchema(BaseSchema):
    id: Optional[int] = None

class SampleListSchema(BaseListSchema):
    super()