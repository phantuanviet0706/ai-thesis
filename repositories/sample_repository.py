from sqlalchemy.orm import Session
from entity.sample_model import SampleModel
from repositories.base_repository import BaseRepository


class SampleRepository(BaseRepository[SampleModel]):
    def __init__(self, db: Session):
        """
        @desc Khởi tạo repository mẫu với phiên làm việc cơ sở dữ liệu và model SampleModel
        @params db (Session): Phiên làm việc SQLAlchemy dùng để thao tác với bảng dữ liệu mẫu
        """
        super().__init__(db, SampleModel)