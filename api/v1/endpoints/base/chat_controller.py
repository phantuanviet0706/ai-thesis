import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from fastapi_utils.cbv import cbv

from api.deps import optional_auth, require_auth
from core.logger import custom_logger
from schemas.api_schema import ApiResponse
from schemas.chat_schema import ChatRequest, ChatResponse
from services.chat_service import ChatService

router = APIRouter()


@cbv(router)
class ChatController:
    service: ChatService = Depends()

    @router.post("/", response_model=ApiResponse[ChatResponse])
    async def chat(
        self,
        request: ChatRequest,
        token_payload: dict = Depends(require_auth),
    ):
        """
        @desc Endpoint chat đồng bộ với timeout 30 giây. Yêu cầu token JWT Bearer hợp lệ. Gọi service xử lý chat và trả về phản hồi hoàn chỉnh sau khi hoàn tất.
        @params request (ChatRequest): Dữ liệu yêu cầu chat gồm session_id, message và channel
        @params token_payload (dict): Payload token JWT đã xác thực, chứa thông tin người dùng
        @return ApiResponse[ChatResponse]: Phản hồi chứa kết quả chat từ hệ thống đa tác nhân
        """
        custom_logger.info(
            f"[ChatController] POST /chat | session={request.session_id} | "
            f"channel={request.channel} | user={token_payload.get('sub')}"
        )
        try:
            response = await asyncio.wait_for(
                self.service.handle_chat(request), timeout=30.0
            )
            return ApiResponse(code=200, message="Success", result=response)
        except asyncio.TimeoutError:
            custom_logger.warning(
                f"[ChatController] Timeout 30s exceeded | session={request.session_id}"
            )
            raise HTTPException(status_code=504, detail="Request timeout — MAS exceeded 30s")
        except Exception as exc:
            custom_logger.error(
                f"[ChatController] Unhandled error | session={request.session_id} | error={exc}",
                exc_info=True,
            )
            raise HTTPException(status_code=500, detail=str(exc))

    @router.get("/stream")
    async def chat_stream(
        self,
        message: str,
        session_id: str | None = None,
        channel: str = "web",
        token_payload: dict | None = Depends(optional_auth),
    ):
        """
        @desc Endpoint Server-Sent Events — truyền trực tiếp từng token từ Synth Agent khi chúng được sinh ra. Xác thực là tùy chọn để hỗ trợ nhúng trực tiếp trên trình duyệt. Mỗi sự kiện SSE là một JSON: {"token": str, "done": false}. Sự kiện cuối cùng: {"done": true, "session_id": ..., "psych_state": ...}.
        @params message (str): Nội dung tin nhắn của người dùng
        @params session_id (str | None): Mã định danh phiên hội thoại, tùy chọn
        @params channel (str): Kênh giao tiếp, mặc định là "web"
        @params token_payload (dict | None): Payload token JWT nếu có xác thực, hoặc None nếu là khách
        @return StreamingResponse: Luồng phản hồi SSE dạng text/event-stream
        """
        user_sub = token_payload.get("sub") if token_payload else "guest"
        custom_logger.info(
            f"[ChatController] GET /chat/stream | session={session_id} | "
            f"channel={channel} | user={user_sub}"
        )
        request = ChatRequest(session_id=session_id, message=message, channel=channel)

        async def event_generator():
            """
            @desc Hàm generator bất đồng bộ tạo ra các sự kiện SSE từ luồng dữ liệu chat. Duyệt qua từng payload từ service và định dạng thành chuỗi SSE. Bắt lỗi và gửi sự kiện lỗi cuối cùng nếu xảy ra ngoại lệ.
            """
            try:
                async for payload in self.service.stream_chat(request):
                    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            except Exception as exc:
                custom_logger.error(
                    f"[ChatController] SSE generator error | session={session_id} | error={exc}",
                    exc_info=True,
                )
                yield f"data: {json.dumps({'error': str(exc), 'done': True})}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
