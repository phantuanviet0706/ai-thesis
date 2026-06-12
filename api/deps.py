from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError

from core.security import decode_token

_bearer = HTTPBearer(auto_error=False)


def require_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict | None:
    """
    @desc Dependency của FastAPI — yêu cầu token JWT Bearer hợp lệ. Trả về payload đã giải mã (bao gồm 'sub' = định danh người dùng). Ném lỗi 401 nếu token thiếu hoặc không hợp lệ.
    @params credentials (HTTPAuthorizationCredentials | None): Thông tin xác thực Bearer được trích xuất tự động từ header Authorization
    @return dict | None: Payload của token sau khi giải mã thành công
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide a Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_token(credentials.credentials)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


def optional_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict | None:
    """
    @desc Dependency của FastAPI — xác thực token JWT Bearer nếu có, ngược lại trả về None (khách vãng lai). Không ném lỗi khi token vắng mặt hoặc không hợp lệ.
    @params credentials (HTTPAuthorizationCredentials | None): Thông tin xác thực Bearer được trích xuất tự động từ header Authorization
    @return dict | None: Payload của token nếu hợp lệ, hoặc None nếu không có token
    """
    if credentials is None:
        return None
    try:
        return decode_token(credentials.credentials)
    except JWTError:
        return None
