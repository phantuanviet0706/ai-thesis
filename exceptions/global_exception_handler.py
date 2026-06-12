from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from starlette.responses import JSONResponse

from constants.error_code import ErrorCode
from core.logger import custom_logger
from exceptions.app_exception import AppException
from schemas.api_schema import ApiResponse


def register_exception_handler(app: FastAPI):
    """
    @desc Đăng ký tất cả các handler xử lý ngoại lệ toàn cục vào ứng dụng FastAPI. Bao gồm handler cho AppException, Exception chung và RequestValidationError.
    @params app (FastAPI): Đối tượng ứng dụng FastAPI cần đăng ký các handler ngoại lệ
    """

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        """
        @desc Xử lý ngoại lệ AppException — lấy thông tin mã lỗi và trả về JSONResponse với HTTP status và nội dung lỗi tương ứng. Ghi log cảnh báo kèm đường dẫn và chi tiết lỗi.
        @params request (Request): Đối tượng yêu cầu HTTP chứa thông tin đường dẫn
        @params exc (AppException): Ngoại lệ ứng dụng chứa mã lỗi định nghĩa sẵn
        @return JSONResponse: Phản hồi JSON với HTTP status và nội dung lỗi tương ứng
        """
        error_code = exc.error_code
        custom_logger.warning(
            f"[Exception] AppException | path={request.url.path} | "
            f"code={error_code.code} | message={error_code.message}"
        )
        return JSONResponse(
            status_code=error_code.http_status,
            content=ApiResponse(
                code=error_code.code,
                message=str(error_code.message)
            ).model_dump()
        )

    @app.exception_handler(Exception)
    async def uncategorized_exception_handler(request: Request, exc: Exception):
        """
        @desc Xử lý tất cả ngoại lệ chưa được phân loại — ghi log lỗi nghiêm trọng kèm stack trace và trả về JSONResponse 500 với mã lỗi UNCATEGORIZED_EXCEPTION.
        @params request (Request): Đối tượng yêu cầu HTTP chứa thông tin đường dẫn
        @params exc (Exception): Ngoại lệ bất kỳ chưa được xử lý bởi handler cụ thể
        @return JSONResponse: Phản hồi JSON 500 với thông báo lỗi nội bộ
        """
        custom_logger.error(
            f"[Exception] Unhandled {type(exc).__name__} | "
            f"path={request.url.path} | error={str(exc)}",
            exc_info=True,
        )
        error_code = ErrorCode.UNCATEGORIZED_EXCEPTION
        return JSONResponse(
            status_code=error_code.http_status,
            content=ApiResponse(
                code=error_code.code,
                message=error_code.message,
                result=None
            ).model_dump()
        )

    @app.exception_handler(RequestValidationError)
    async def custom_validation_exception_handler(request: Request, exc: RequestValidationError):
        """
        @desc Xử lý lỗi xác thực dữ liệu đầu vào từ Pydantic/FastAPI — định dạng danh sách lỗi chi tiết, ghi log cảnh báo và trả về JSONResponse với mã lỗi VALIDATION_ERROR.
        @params request (Request): Đối tượng yêu cầu HTTP chứa thông tin đường dẫn
        @params exc (RequestValidationError): Ngoại lệ xác thực chứa danh sách lỗi từng trường
        @return JSONResponse: Phản hồi JSON với danh sách chi tiết lỗi xác thực
        """
        errors = exc.errors()
        error_details = [
            f"{' -> '.join(map(str, e['loc']))}: {e['msg']}" for e in errors
        ]
        custom_logger.warning(
            f"[Exception] ValidationError | path={request.url.path} | "
            f"details={error_details}"
        )
        error_code = ErrorCode.VALIDATION_ERROR
        return JSONResponse(
            status_code=error_code.status_code,
            content=ApiResponse(
                code=error_code.code,
                message=error_code.message,
                result={"details": error_details}
            ).model_dump()
        )
