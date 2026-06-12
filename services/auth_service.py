from datetime import timedelta

from fastapi.params import Depends
from sqlalchemy.orm import Session

from constants.error_code import ErrorCode
from core.security import verify_password, get_vpid_hash, create_access_token, create_refresh_token, decode_token
from exceptions.app_exception import AppException
from repositories.user_repository import UserRepository
from schemas.auth_schema import AuthLogin
from database.mysql_manager import mysql_manager
from infrastructure.redis_client import redis_client

manager = mysql_manager

class AuthService:
    def __init__(self, db: Session = Depends(manager.get_db)):
        """
        @desc Khởi tạo AuthService với session cơ sở dữ liệu được inject qua dependency injection của FastAPI
        @params db (Session): Phiên làm việc với cơ sở dữ liệu MySQL
        """
        self.db = db

    def login_token(self, data: AuthLogin):
        """
        @desc Xác thực thông tin đăng nhập, tạo access token và refresh token, lưu refresh token vào Redis
        @params data (AuthLogin): Dữ liệu đăng nhập gồm username, password và visitor_id
        @return dict: Dictionary chứa refresh_token, access_token và thông tin người dùng
        """
        user = UserRepository.get_by_username(self.db, data.username)
        if not user:
            raise AppException(ErrorCode.USER_NOT_FOUND)

        if not verify_password(data.password, user.password):
            raise AppException(ErrorCode.UNAUTHENTICATED)

        user_id = user.id

        vpid_hash = get_vpid_hash(data.visitor_id)
        access_token = create_access_token(data={"sub": str(user_id)})
        refresh_token = create_refresh_token(data={"sub": str(user_id)}, visitor_id=data.visitor_id)

        redis_key = f"refresh_token:{user_id}:{vpid_hash}"
        redis_client.setex(redis_key, timedelta(days=7), refresh_token)

        return {
            "refresh_token": refresh_token,
            "access_token": access_token,
            "user": user
        }

    def refresh_token(
            self,
            rt_cookie: str,
            visitor_id: str,
    ):
        """
        @desc Xác minh refresh token từ cookie, kiểm tra tính hợp lệ với Redis và thiết bị, sau đó cấp cặp token mới
        @params rt_cookie (str): Refresh token lấy từ cookie của người dùng
        @params visitor_id (str): Định danh thiết bị của người dùng dùng để xác minh tính nhất quán
        @return dict: Dictionary chứa access_token và refresh_token mới
        """
        payload = decode_token(rt_cookie)
        if not payload or payload.get("type") != "refresh":
            raise AppException(ErrorCode.UNAUTHENTICATED)

        user_id = payload.get("sub")
        vpid_hash_in_token = payload.get("vpid")

        current_vpid_hash = get_vpid_hash(visitor_id)
        if current_vpid_hash != vpid_hash_in_token:
            raise AppException(ErrorCode.NOT_MATCHING_DEVICE)

        redis_key = f"refresh_token:{user_id}:{vpid_hash_in_token}"
        saved_token = redis_client.get(redis_key)

        if not saved_token:
            raise AppException(ErrorCode.TOKEN_EXPIRES)

        if saved_token != rt_cookie:
            raise AppException(ErrorCode.SECURITY_ALERT)

        new_at = create_access_token(data={"sub": user_id})
        new_rt = create_refresh_token(data={"sub": user_id}, visitor_id=visitor_id)

        redis_client.setex(redis_key, timedelta(days=7), new_rt)

        return {
            "access_token": new_at,
            "refresh_token": new_rt
        }
