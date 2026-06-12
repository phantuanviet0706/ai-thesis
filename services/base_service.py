from typing import TypeVar, Generic, List, Any, Optional

from pydantic import BaseModel

from constants.error_code import ErrorCode
from exceptions.app_exception import AppException

T = TypeVar('T')
R = TypeVar('R')
S = TypeVar('S', bound=BaseModel)

class BaseService(Generic[T, R]):
    def __init__(self, repo: R):
        """
        @desc Khởi tạo BaseService với repository tương ứng để thực hiện các thao tác CRUD
        @params repo (R): Đối tượng repository cung cấp các phương thức truy cập dữ liệu
        """
        self.repo = repo

    def get_all(self) -> List[T]:
        """
        @desc Lấy toàn bộ danh sách bản ghi từ repository
        @return List[T]: Danh sách tất cả các bản ghi trong cơ sở dữ liệu
        """
        return self.repo.get_all()

    def get_by_id(self, id: Any) -> T:
        """
        @desc Lấy một bản ghi theo ID — ném ngoại lệ nếu không tìm thấy
        @params id (Any): Giá trị định danh của bản ghi cần tìm
        @return T: Đối tượng bản ghi tương ứng với ID được cung cấp
        """
        item = self.repo.get_by_id(id)
        if not item:
            raise AppException(ErrorCode.UNCATEGORIZED_EXCEPTION)
        return item

    def delete(self, id: Any) -> T:
        """
        @desc Xóa bản ghi theo ID và trả về đối tượng vừa bị xóa
        @params id (Any): Giá trị định danh của bản ghi cần xóa
        @return T: Đối tượng bản ghi đã bị xóa
        """
        item = self.repo.get_by_id(id)
        self.repo.delete(item)
        return item