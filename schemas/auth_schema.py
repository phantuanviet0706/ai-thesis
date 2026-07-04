from schemas.base_schema import BaseSchema


class AuthLogin(BaseSchema):
    username: str
    password: str
    visitor_id: str