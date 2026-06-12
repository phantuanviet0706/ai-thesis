from sqlalchemy import text
from sqlalchemy.orm import Session

from entity import User
from repositories.base_repository import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, db: Session):
        """
        @desc Khởi tạo repository quản lý người dùng với phiên làm việc cơ sở dữ liệu
        @params db (Session): Phiên làm việc SQLAlchemy dùng để thao tác với bảng người dùng
        """
        super().__init__(db, User)

    def get_by_username(self, username: str):
        """
        @desc Tìm kiếm người dùng theo tên đăng nhập
        @params username (str): Tên đăng nhập cần tìm kiếm
        @return User | None: Đối tượng người dùng nếu tìm thấy, hoặc None nếu không tồn tại
        """
        return self.db.query(User).filter(User.username == username).first()
