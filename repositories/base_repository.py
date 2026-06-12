from typing import TypeVar, Generic, Type, Optional, List, Any

from sqlalchemy import Boolean
from sqlalchemy.orm import Session

from constants.error_code import ErrorCode
from core.logger import custom_logger
from exceptions.app_exception import AppException

T = TypeVar('T')

class BaseRepository(Generic[T]):
    def __init__(self, db: Session, model: Type[T]):
        """
        @desc Khởi tạo repository với phiên làm việc cơ sở dữ liệu và lớp model tương ứng
        @params db (Session): Phiên làm việc SQLAlchemy dùng để thực hiện các thao tác với cơ sở dữ liệu
        @params model (Type[T]): Lớp entity/model SQLAlchemy mà repository này quản lý
        """
        self.db = db
        self.model = model

    def get_by_id(self, id: int) -> Optional[T]:
        """
        @desc Lấy một bản ghi theo ID
        @params id (int): Giá trị khóa chính của bản ghi cần tìm
        @return Optional[T]: Bản ghi tìm được hoặc None nếu không tồn tại
        """
        return self.db.query(self.model).filter(self.model.id == id).first()

    def get_by_ids(self, ids: list) -> List[T]:
        """
        @desc Lấy danh sách các bản ghi theo nhiều ID cùng lúc
        @params ids (list): Danh sách các giá trị khóa chính cần truy vấn
        @return List[T]: Danh sách các bản ghi tìm được
        """
        return self.db.query(self.model).filter(self.model.id.in_(ids)).all()

    def get_all(self) -> List[T]:
        """
        @desc Lấy toàn bộ danh sách bản ghi trong bảng
        @return List[T]: Danh sách tất cả các bản ghi hiện có
        """
        return self.db.query(self.model).all()

    def find_by_filter(self, **kwargs) -> List[T]:
        """
        @desc Tìm kiếm linh hoạt theo một hoặc nhiều trường cụ thể, ví dụ: find_by_filter(email="abc@gmail.com")
        @params kwargs (dict): Các cặp tên trường và giá trị cần lọc
        @return List[T]: Danh sách các bản ghi thỏa mãn điều kiện lọc
        """
        return self.db.query(self.model).filter_by(**kwargs).all()

    def get_paginate(self, page: int = 1, limit: int = 10) -> List[T]:
        """
        @desc Lấy danh sách bản ghi theo trang với số lượng giới hạn trên mỗi trang
        @params page (int): Số trang cần lấy, bắt đầu từ 1, mặc định là 1
        @params limit (int): Số lượng bản ghi tối đa trên mỗi trang, mặc định là 10
        @return List[T]: Danh sách các bản ghi thuộc trang được yêu cầu
        """
        offset = (page - 1) * limit
        return self.db.query(self.model).offset(offset).limit(limit).all()

    def save(self, item: T, is_commit: Boolean = True) -> T:
        """
        @desc Lưu một bản ghi vào cơ sở dữ liệu, có thể commit ngay hoặc chỉ flush tùy tham số
        @params item (T): Đối tượng entity cần lưu
        @params is_commit (Boolean): Nếu True sẽ commit ngay, nếu False chỉ flush để lấy ID, mặc định là True
        @return T: Đối tượng entity đã được lưu
        """
        try:
            self.db.add(item)
            if is_commit:
                self.db.commit()
            else:
                self.db.flush()
            return item
        except Exception as e:
            self.db.rollback()
            custom_logger.error(str(e))
            raise AppException(ErrorCode.FAILED_TO_UPSERT)

    def save_all(self, items: list[T], is_commit: Boolean = True) -> list[T]:
        """
        @desc Lưu hàng loạt nhiều bản ghi vào cơ sở dữ liệu trong một lần gọi
        @params items (list[T]): Danh sách các đối tượng entity cần lưu
        @params is_commit (Boolean): Nếu True sẽ commit ngay, nếu False chỉ flush, mặc định là True
        @return list[T]: Danh sách các đối tượng entity đã được lưu
        """
        try:
            self.db.add_all(items)
            if is_commit:
                self.db.commit()
            else:
                self.db.flush()
            return items
        except Exception as e:
            self.db.rollback()
            custom_logger.error(f"Batch update failed: {str(e)}")
            raise AppException(ErrorCode.FAILED_TO_UPSERT)

    def add(self, item: T) -> T:
        """
        @desc Thêm bản ghi vào session và flush để lấy ID mà chưa commit, dùng khi muốn kiểm soát commit ở tầng Service
        @params item (T): Đối tượng entity cần thêm vào session
        @return T: Đối tượng entity sau khi flush (đã có ID được gán)
        """
        self.db.add(item)
        self.db.flush()
        return item

    def delete(self, item: T) -> bool:
        """
        @desc Xóa một bản ghi khỏi cơ sở dữ liệu và commit thay đổi
        @params item (T): Đối tượng entity cần xóa
        @return bool: True nếu xóa thành công
        """
        try:
            self.db.delete(item)
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            custom_logger.error(str(e))
            raise AppException(ErrorCode.FAILED_TO_DELETE)

    def delete_by_id(self, id: Any) -> bool:
        """
        @desc Tìm và xóa bản ghi theo ID, trả về False nếu không tìm thấy bản ghi
        @params id (Any): Giá trị khóa chính của bản ghi cần xóa
        @return bool: True nếu tìm thấy và xóa thành công, False nếu không tìm thấy
        """
        item = self.get_by_id(id)
        if item:
            return self.delete(item)
        return False

    def count(self) -> int:
        """
        @desc Đếm tổng số bản ghi hiện có trong bảng
        @return int: Tổng số bản ghi trong bảng
        """
        return self.db.query(self.model).count()