from fastapi import APIRouter, Response
from fastapi.params import Body, Depends
from fastapi_utils.cbv import cbv
from starlette.requests import Request

from constants.error_code import ErrorCode
from exceptions.app_exception import AppException
from schemas.api_schema import ApiResponse
from schemas.auth_schema import AuthLogin
from services.auth_service import AuthService

router = APIRouter()

@cbv(router)
class AuthController:
    service: AuthService = Depends()

    @router.post("/login")
    async def login(self, response: Response, data: AuthLogin):
        """
        @desc Xử lý đăng nhập người dùng, tạo access token và refresh token. Refresh token được lưu vào cookie HttpOnly, access token được trả về trong body phản hồi.
        @params response (Response): Đối tượng phản hồi FastAPI dùng để ghi cookie
        @params data (AuthLogin): Dữ liệu đăng nhập gồm tên đăng nhập và mật khẩu
        @return ApiResponse: Phản hồi chứa access_token và tên hiển thị của người dùng
        """
        data_response = self.service.login_token(data)
        response.set_cookie(key="refresh_token", value=data_response['refresh_token'], httponly=True,
                            path="/api/v1/auth/refresh")
        return ApiResponse(code=1, message="Đăng nhập thành công", result={
            "access_token": data_response['access_token'],
            "name": data_response['user'].fullname or data_response['user'].username,
        })

    @router.post("/refresh")
    async def refresh(self, request: Request, response: Response, body: dict = Body(...)):
        """
        @desc Làm mới access token bằng refresh token lấy từ cookie HttpOnly. Cấp refresh token mới và cập nhật lại cookie, đồng thời trả về access token mới trong body phản hồi.
        @params request (Request): Đối tượng yêu cầu FastAPI dùng để đọc cookie refresh_token
        @params response (Response): Đối tượng phản hồi FastAPI dùng để ghi cookie mới
        @params body (dict): Body của yêu cầu, có thể chứa visitor_id để nhận dạng phiên
        @return ApiResponse: Phản hồi chứa access_token mới
        """
        rt_cookie = request.cookies.get("refresh_token")
        if not rt_cookie:
            raise AppException(ErrorCode.REFRESH_TOKEN_MISSING)

        visitor_id = body.get("visitor_id")
        data_response = self.service.refresh_token(rt_cookie, visitor_id)

        response.set_cookie(key="refresh_token", value=data_response['refresh_token'], httponly=True,
                            path="/api/v1/auth/refresh")
        return ApiResponse(code=1, message="Lấy token thành công", result={
            "access_token": data_response['access_token'],
        })