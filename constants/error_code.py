from enum import Enum

from starlette import status


class ErrorCode(Enum):
    USER_NOT_FOUND = (1001, "Người dùng không tồn tại", status.HTTP_400_BAD_REQUEST)


    COMMON_VALIDATOR_DATE = (1998, "Ngày bắt đầu không được lớn hơn ngày kết thúc", status.HTTP_400_BAD_REQUEST)
    VALIDATION_ERROR = (1998, "Dữ liệu đầu vào không hợp lệ", status.HTTP_400_BAD_REQUEST)

    UNAUTHENTICATED = (1999, "Chưa xác minh", status.HTTP_401_UNAUTHORIZED)
    TOKEN_EXPIRES = (1999, "Phiên đăng nhập đã hết hạn hoặc bị chặn", status.HTTP_401_UNAUTHORIZED)
    REFRESH_TOKEN_MISSING = (1999, "Thiếu Refresh Token", status.HTTP_401_UNAUTHORIZED)
    NOT_MATCHING_DEVICE = (1999, "Thiết bị không khớp", status.HTTP_403_FORBIDDEN)
    SECURITY_ALERT = (1999, "Cảnh báo bảo mật: Token đã được dùng trước đó", status.HTTP_403_FORBIDDEN)

    FAILED_TO_UPSERT = (1999, "Không thể tương tác Object với DB, vui lòng thử lại!", status.HTTP_500_INTERNAL_SERVER_ERROR)
    FAILED_TO_DELETE = (1999, "Không thể xóa Object, vui lòng thử lại!", status.HTTP_500_INTERNAL_SERVER_ERROR)

    UNCATEGORIZED_EXCEPTION = (9999, "Lỗi không xác định", status.HTTP_500_INTERNAL_SERVER_ERROR)

    def __init__(self, code: int, message: str, http_status: int):
        self.code = code
        self.message = message
        self.http_status = http_status