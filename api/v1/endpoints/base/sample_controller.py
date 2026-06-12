from fastapi import APIRouter, Depends
from fastapi_utils import cbv

from schemas.api_schema import ApiResponse
from services.sample_service import SampleService

router = APIRouter()

@cbv(router)
class SampleController:
    service: SampleService = Depends()

    @router.get("/check")
    async def check(self):
        """
        @desc Kiểm tra trạng thái hoạt động của Sample Service. Trả về phản hồi xác nhận service đang chạy bình thường.
        @return ApiResponse: Phản hồi xác nhận trạng thái của Sample Service
        """
        return ApiResponse(
            code=1,
            message="Sample Service Check"
        )
