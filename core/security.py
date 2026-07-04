import hashlib

from datetime import datetime, timedelta
from typing import Optional

from dotenv import load_dotenv
from jose import JWTError, jwt, ExpiredSignatureError
from passlib.context import CryptContext

from core.config import settings

load_dotenv()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM


def get_vpid_hash(visitor_id: str) -> str:
    """
    @desc Tạo chuỗi hash SHA-256 từ visitor ID kết hợp với SECRET_KEY để định danh an toàn
    @params visitor_id (str): Mã định danh của khách truy cập cần được hash
    @return str: Chuỗi hash SHA-256 dưới dạng hexadecimal
    """
    return hashlib.sha256(f"{visitor_id}{SECRET_KEY}".encode()).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    @desc Xác minh mật khẩu thuần văn bản có khớp với mật khẩu đã được băm hay không
    @params plain_password (str): Mật khẩu gốc dạng thuần văn bản cần kiểm tra
    @params hashed_password (str): Mật khẩu đã được băm lưu trong cơ sở dữ liệu
    @return bool: True nếu mật khẩu khớp, False nếu không khớp
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    @desc Băm mật khẩu bằng thuật toán bcrypt trước khi lưu vào cơ sở dữ liệu
    @params password (str): Mật khẩu gốc dạng thuần văn bản cần được băm
    @return str: Chuỗi mật khẩu đã được băm bằng bcrypt
    """
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    @desc Tạo JWT access token với thời hạn mặc định 15 phút hoặc theo tham số tùy chỉnh
    @params data (dict): Dữ liệu cần mã hóa vào token (ví dụ: {"user_id": 1, "system_id": 1})
    @params expires_delta (Optional[timedelta]): Thời gian hết hạn tùy chỉnh, mặc định là 15 phút nếu không truyền
    @return str: Chuỗi JWT access token đã được mã hóa
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    """
    @desc Giải mã JWT token và trả về payload, xử lý các trường hợp token hết hạn hoặc không hợp lệ
    @params token (str): Chuỗi JWT token cần giải mã
    @return Optional[dict]: Dict payload nếu hợp lệ, -1 nếu token hết hạn, None nếu token không hợp lệ
    """
    try:
        payload = jwt.decode(token=token, key=SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except ExpiredSignatureError:
        return -1
    except JWTError:
        return None


def create_refresh_token(data: dict, visitor_id: str) -> str:
    """
    @desc Tạo JWT refresh token với thời hạn 7 ngày, bao gồm hash của visitor ID để tăng bảo mật
    @params data (dict): Dữ liệu cần mã hóa vào token
    @params visitor_id (str): Mã định danh khách truy cập dùng để tạo vpid hash gắn vào token
    @return str: Chuỗi JWT refresh token đã được mã hóa với thời hạn 7 ngày
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=7)

    vpid_hash = get_vpid_hash(visitor_id)

    to_encode.update({"exp": expire, "type": "refresh", "vpid": vpid_hash})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt