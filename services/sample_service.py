from sqlalchemy.orm import Session

from entity.sample_model import SampleModel
from repositories.sample_repository import SampleRepository
from services.base_service import BaseService


class SampleService(BaseService[SampleModel, SampleRepository]):
    def __init__(self, db: Session):
        """
        @desc Khởi tạo SampleService với session cơ sở dữ liệu và tạo SampleRepository tương ứng
        @params db (Session): Phiên làm việc với cơ sở dữ liệu
        """
        self.repo = SampleRepository(db)
        super().__init__(self.repo)