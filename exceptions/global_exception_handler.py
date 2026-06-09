from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from starlette.responses import JSONResponse

from constants.error_code import ErrorCode
from schemas.api_schema import ApiResponse
from exceptions.app_exception import AppException


def register_exception_handler(app: FastAPI):

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        error_code = exc.error_code
        return JSONResponse(
            status_code=error_code.http_status,
            content=ApiResponse(
                code=error_code.code,
                message=str(error_code.message)
            ).model_dump()
        )

    @app.exception_handler(Exception)
    async def uncategorized_exception_handler(request: Request, exc: Exception):
        print(f"Lỗi chưa được phân loại: {str(exc)}")

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
        errors = exc.errors()

        error_details = []
        for error in errors:
            loc = " -> ".join(map(str, error["loc"]))
            msg = error["msg"]
            error_details.append(f"{loc}: {msg}")

        error_code = ErrorCode.VALIDATION_ERROR
        return JSONResponse(
            status_code=error_code.status_code,
            content=ApiResponse(
                code=error_code.code,
                message=error_code.message,
                result={"details": error_details}
            ).model_dump()
        )