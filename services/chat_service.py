import asyncio
import time
import uuid
from collections.abc import AsyncGenerator
from typing import Any

from langchain_core.messages import HumanMessage

from core.logger import custom_logger
from database import get_db, run_with_deadlock_retry
from entity.product_doc import ProductDoc
from graph.graph import get_compiled_graph
from graph.state import PsychState
from repositories.business_repository import BusinessRepository
from repositories.conversation_repository import ConversationRepository
from repositories.product_repository import ProductRepository
from schemas.chat_schema import ChatRequest, ChatResponse
from services.business_service import BusinessService

# Giới hạn số ảnh gửi cho khách trong 1 lượt — tránh spam chatbox nếu 1 sản phẩm có
# quá nhiều ảnh trong tương lai (hiện tại mỗi sản phẩm có 2 ảnh, xem seed.sql).
_MAX_IMAGES_PER_TURN = 5


_business_service = BusinessService()


async def _safe_task(coro, label: str) -> None:
    """Wrapper cho asyncio.create_task — đảm bảo exception từ background task luôn được log."""
    try:
        await coro
    except Exception as exc:
        custom_logger.error(
            f"[Background task failed] {label} | {exc}", exc_info=True
        )


class ChatService:

    async def reset_session(self, session_id: str) -> None:
        """
        @desc Xóa checkpoint LangGraph của đúng 1 session (theo thread_id) — dùng cho lệnh /reset
        của các adapter (Telegram, v.v). Không đụng đến session/dữ liệu của người dùng khác, và
        không đụng MySQL/ChromaDB (chỉ xóa bộ nhớ hội thoại đang lưu ở checkpointer).
        @params session_id (str): Session key / thread_id cần xóa (vd "telegram:pancharm:123456789")
        """
        graph = await get_compiled_graph()
        if not graph.checkpointer:
            custom_logger.warning(f"[ChatService] reset_session skipped | no checkpointer configured")
            return
        try:
            await graph.checkpointer.adelete_thread(session_id)
            custom_logger.info(f"[ChatService] session checkpoint deleted | session={session_id}")
        except Exception as exc:
            custom_logger.error(
                f"[ChatService] reset_session failed | session={session_id} | error={exc}",
                exc_info=True,
            )

    async def handle_chat(self, request: ChatRequest) -> ChatResponse:
        """
        @desc Xử lý một yêu cầu chat đầy đủ — chạy toàn bộ pipeline graph và trả về phản hồi cuối cùng, đồng thời lưu lượt hội thoại vào cơ sở dữ liệu bất đồng bộ
        @params request (ChatRequest): Đối tượng yêu cầu chứa tin nhắn, session_id, channel và user_id
        @return ChatResponse: Đối tượng phản hồi chứa kết quả từ graph cùng các thông tin phân tích tâm lý và sản phẩm
        """
        session_id = request.session_id or str(uuid.uuid4())
        is_new = request.session_id is None

        custom_logger.info(
            f"[ChatService] handle_chat | session={session_id} | "
            f"channel={request.channel} | user_id={request.user_id} | "
            f"new_session={is_new} | msg_len={len(request.message)}"
        )

        graph = await get_compiled_graph()

        config = {"configurable": {"thread_id": session_id}}
        input_state = self._build_input_state(request, session_id)

        custom_logger.info(f"[ChatService] invoking graph | session={session_id}")
        t0 = time.perf_counter()
        result = await graph.ainvoke(input_state, config=config)
        latency_ms = (time.perf_counter() - t0) * 1000

        final_response = result.get("final_response", "")
        psych_state = result.get("psych_state")
        psych_confidence = result.get("psych_confidence") or 0.0
        primary_concern = result.get("primary_concern")
        consult_strategy = result.get("consult_strategy")
        iteration_count = result.get("iteration_count", 0)
        retrieved_products = result.get("retrieved_products", [])
        retrieval_scores = result.get("retrieval_scores", [])
        previous_turn_products = result.get("previous_turn_products", [])
        extracted_info = result.get("extracted_info")
        product_count = len(retrieved_products)

        custom_logger.info(
            f"[ChatService] graph complete | session={session_id} | "
            f"latency={latency_ms:.0f}ms | iterations={iteration_count} | "
            f"products={product_count} | psych={psych_state} | "
            f"response_len={len(final_response)}"
        )

        final_response = await self._post_process_turn(
            session_id=session_id,
            request=request,
            final_response=final_response,
            psych_state=psych_state,
            psych_confidence=psych_confidence,
            primary_concern=primary_concern,
            consult_strategy=consult_strategy,
            iteration_count=iteration_count,
            retrieved_products=retrieved_products,
            retrieval_scores=retrieval_scores,
            extracted_info=extracted_info,
            result_messages=result.get("messages", []),
            latency_ms=latency_ms,
        )

        image_urls = await self._resolve_product_images(
            extracted_info, retrieved_products, previous_turn_products, psych_state
        )

        return ChatResponse(
            session_id=session_id,
            response=final_response,
            psych_state=psych_state,
            psych_confidence=result.get("psych_confidence"),
            consult_strategy=consult_strategy,
            retrieved_product_count=product_count,
            latency_ms=round(latency_ms, 2),
            iteration_count=iteration_count,
            image_urls=image_urls,
        )

    async def _resolve_product_images(
        self,
        extracted_info: dict | None,
        retrieved_products: list[ProductDoc],
        previous_turn_products: list[ProductDoc] | None = None,
        psych_state: PsychState | None = None,
    ) -> list[str]:
        """
        @desc Quyết định có gửi ảnh sản phẩm lượt này không, và đúng sản phẩm nào. Dùng 2 tín hiệu
        BỔ SUNG cho nhau, không tín hiệu nào phụ thuộc lẫn nhau:
          1. Extraction Agent đánh dấu wants_product_image=true (khách xin ảnh rõ ràng, hoặc tham
             chiếu ngược kiểu "mẫu còn lại" — cần suy luận trên lịch sử nên phải qua LLM).
          2. Quy tắc THUẦN CODE: psych_state đã vượt qua CURIOUS (khách đang tập trung vào 1 sản
             phẩm cụ thể, đúng định nghĩa INTERESTED trở lên trong psych_agent.md) → tự động gửi ảnh
             sản phẩm liên quan nhất, KHÔNG cần chờ Extraction Agent.
        Tín hiệu #2 bắt buộc phải THUẦN CODE (không qua LLM riêng) vì Synth Agent và Extraction Agent
        chạy SONG SONG trong cùng 1 lượt (fan-out) và KHÔNG thấy được kết quả của nhau — nếu để 2 LLM
        độc lập tự phán đoán "có nên nói/gửi ảnh không", chúng có thể kết luận khác nhau (Synth nói
        "ảnh gửi kèm" nhưng Extraction không set wants_product_image → không ảnh nào được gửi thật).
        psych_state thì được Psych Agent tính TRƯỚC bước fan-out nên luôn nhất quán giữa lời Synth
        nói và ảnh thực sự đính kèm (xem "GỬI ẢNH TỰ ĐỘNG" trong resources/prompt/synth_agent.md).
        @params extracted_info (dict | None): Kết quả tích lũy từ Extraction Agent (graph/state.py)
        @params retrieved_products (list[ProductDoc]): Sản phẩm KR Agent trả về ở lượt hiện tại
        @params previous_turn_products (list[ProductDoc] | None): Sản phẩm đã gợi ý ở lượt trước
        @params psych_state (PsychState | None): Trạng thái tâm lý đã được Psych Agent xác định lượt này
        @return list[str]: Danh sách URL ảnh cần gửi, rỗng nếu không có tín hiệu nào kích hoạt
        """
        wants_image_explicit = bool(extracted_info and extracted_info.get("wants_product_image"))
        auto_attach = psych_state is not None and psych_state != PsychState.CURIOUS

        if not wants_image_explicit and not auto_attach:
            return []

        product_id: int | None = None
        selected_ids = extracted_info.get("selected_product_ids") if extracted_info else None

        if wants_image_explicit:
            # Yêu cầu tường minh (thường là tham chiếu ngược kiểu "mẫu còn lại") — ưu tiên
            # selected_product_ids do Extraction Agent resolve qua lịch sử hội thoại, vì
            # retrieved_products của lượt này có thể không liên quan khi câu hỏi mơ hồ.
            for raw_id in selected_ids or []:
                try:
                    product_id = int(raw_id)
                    break
                except (TypeError, ValueError):
                    continue
            fallback_order = (previous_turn_products or [], retrieved_products)
        else:
            # Auto-attach thuần code (psych_state != CURIOUS, không có yêu cầu tường minh) — ưu
            # tiên retrieved_products[0] TRƯỚC selected_product_ids, vì đây đúng là kết quả KR Agent
            # tìm cho CÂU HỎI HIỆN TẠI. Quan trọng khi khách vừa hỏi chi tiết sản phẩm 1 xong lại
            # chuyển sang hỏi sản phẩm 2 khác — nếu ưu tiên selected_product_ids (có thể vẫn còn
            # trỏ tới sản phẩm 1 do Extraction Agent chạy song song, không chắc theo kịp), ảnh gửi
            # sẽ SAI thành sản phẩm 1 dù khách đang hỏi sản phẩm 2.
            fallback_order = (retrieved_products, previous_turn_products or [])

        if product_id is None:
            for fallback_products in fallback_order:
                if not fallback_products:
                    continue
                try:
                    product_id = int(fallback_products[0].id)
                    break
                except (TypeError, ValueError):
                    continue

        if product_id is None and not wants_image_explicit:
            # Vẫn chưa resolve được từ retrieved_products/previous_turn_products (vd cả 2 đều rỗng)
            # → thử nốt selected_product_ids như phương án cuối cho auto-attach.
            for raw_id in selected_ids or []:
                try:
                    product_id = int(raw_id)
                    break
                except (TypeError, ValueError):
                    continue

        if product_id is None:
            custom_logger.info(
                f"[ChatService] muốn gửi ảnh (explicit={wants_image_explicit}, auto={auto_attach}) "
                f"nhưng không resolve được product_id"
            )
            return []

        try:
            urls = await asyncio.to_thread(self._get_product_image_urls_sync, product_id)
        except Exception as exc:
            custom_logger.warning(f"[ChatService] resolve product images failed | product_id={product_id} | {exc}")
            return []

        custom_logger.info(f"[ChatService] resolved {len(urls)} image(s) for product_id={product_id}")
        return urls[:_MAX_IMAGES_PER_TURN]

    def _get_product_image_urls_sync(self, product_id: int) -> list[str]:
        with get_db() as db:
            repo = ProductRepository(db)
            images_by_product = repo.get_images_for_products([product_id])
            images = images_by_product.get(product_id, [])
            return [img.url for img in images]

    async def _post_process_turn(
        self,
        session_id: str,
        request: ChatRequest,
        final_response: str,
        psych_state: Any,
        psych_confidence: float,
        primary_concern: str | None,
        consult_strategy: str | None,
        iteration_count: int,
        retrieved_products: list[ProductDoc],
        retrieval_scores: list[float],
        extracted_info: dict | None,
        result_messages: list,
        latency_ms: float,
    ) -> str:
        """
        @desc Side-effects sau khi graph trả kết quả — dùng chung cho handle_chat (blocking) và
        stream_chat (streaming): persist lượt hội thoại, tạo Order nếu đã đủ điều kiện "purchased",
        dispatch BusinessService (ML logs, ChromaDB training data)
        @return final_response đã được nối thêm mã đơn hàng nếu có tạo order
        """
        session_transcript = [
            ("user" if getattr(m, "type", "") == "human" else "assistant", str(m.content))
            for m in result_messages
            if hasattr(m, "content") and m.content
        ]

        # Tạo order đồng bộ CHỈ khi đã đủ điều kiện "purchased" (sản phẩm + SĐT + địa chỉ)
        # — không tạo đơn thật chỉ vì order_intent=true ở giai đoạn added_to_cart (chưa đủ thông tin giao hàng)
        pre_created_order_id = None
        if (
            extracted_info
            and extracted_info.get("order_intent")
            and extracted_info.get("conversion_outcome") == "purchased"
            and extracted_info.get("customer_phone")
            and extracted_info.get("selected_product_ids")
        ):
            order_code, pre_created_order_id = await asyncio.to_thread(
                self._create_order_sync,
                session_id, extracted_info, retrieved_products,
            )
            if order_code:
                final_response = (
                    final_response.rstrip()
                    + f"\n\n📦 **Mã đơn hàng của bạn: {order_code}**\n"
                    "Lưu mã này để tra cứu trạng thái đơn hàng bất cứ lúc nào nhé!"
                )
                custom_logger.info(f"[ChatService] order created sync | code={order_code} | session={session_id}")

        # _persist_turn_async và _business_service.process_turn_async đều UPDATE cùng 1 dòng
        # ConversationSessions — chạy như 2 asyncio.create_task riêng biệt (song song thật, mỗi
        # cái 1 thread qua asyncio.to_thread) từng gây "Deadlock found when trying to get lock"
        # (MySQL 1213) vì cả 2 transaction tranh chấp cùng lúc. Gộp thành 1 chuỗi TUẦN TỰ trong
        # cùng 1 background task để loại bỏ hẳn việc 2 giao dịch này chạy đồng thời.
        async def _persist_then_track_business() -> None:
            await _safe_task(
                self._persist_turn_async(
                    session_id=session_id,
                    user_id=request.user_id,
                    channel=request.channel,
                    user_message=request.message,
                    assistant_response=final_response,
                    psych_state=psych_state.value if psych_state else None,
                    consult_strategy=consult_strategy,
                    iteration_count=iteration_count,
                    latency_ms=round(latency_ms),
                ),
                "persist_turn",
            )
            await _safe_task(
                _business_service.process_turn_async(
                    session_id=session_id,
                    user_message=request.message,
                    final_response=final_response,
                    psych_state=psych_state.value if psych_state else None,
                    psych_confidence=float(psych_confidence),
                    primary_concern=primary_concern,
                    consult_strategy=consult_strategy,
                    extracted_info=extracted_info,
                    retrieved_product_ids=[str(p.id) for p in retrieved_products],
                    top_retrieval_score=max(retrieval_scores, default=0.0),
                    latency_ms=round(latency_ms),
                    turn_number=iteration_count,
                    pre_created_order_id=pre_created_order_id,
                    session_transcript=session_transcript,
                ),
                "biz_process_turn",
            )

        asyncio.create_task(_persist_then_track_business())
        custom_logger.info(f"[ChatService] DB persist + business tasks scheduled | session={session_id}")
        return final_response

    def _create_order_sync(
        self,
        session_id: str,
        extracted_info: dict,
        retrieved_products: list[ProductDoc],
    ) -> tuple[str | None, int | None]:
        """
        @desc Tạo Order đồng bộ trước khi trả response để lấy order_code đưa vào tin nhắn cho khách
        @return (order_code, order_id) hoặc (None, None) nếu không tạo được
        """
        products_by_id = {str(p.id): p for p in retrieved_products}
        # Chỉ dùng sản phẩm khách đã CHỌN RÕ RÀNG (theo Extraction Agent) — không đoán/fallback
        selected_ids = [str(i) for i in (extracted_info.get("selected_product_ids") or [])]

        selected_products = []
        for pid in selected_ids:
            product = products_by_id.get(pid)
            if product:
                price = float(product.sale_price or product.unit_price)
                selected_products.append({
                    "product_id": pid,
                    "name": product.name,
                    "sku": product.sku,
                    "price": price,
                    "quantity": 1,
                })

        if not selected_products:
            return None, None

        try:
            with get_db() as db:
                conv_repo = ConversationRepository(db)
                biz_repo = BusinessRepository(db)

                session = conv_repo.upsert_session(session_id, user_id=None, channel="chatbot")
                user_id = session.user_id

                phone = extracted_info.get("customer_phone")
                if phone:
                    user = biz_repo.upsert_user_by_phone(phone, extracted_info.get("customer_name"))
                    user_id = user.id
                    biz_repo.update_user_profile(user_id, extracted_info)

                order = biz_repo.create_order_from_chat(
                    session_db_id=session.id,
                    user_id=user_id,
                    selected_products=selected_products,
                    notes=f"Đặt qua chatbot | session={session_id}",
                )
                return (order.order_code, order.id) if order else (None, None)
        except Exception as exc:
            custom_logger.error(f"[ChatService] _create_order_sync failed | {exc}", exc_info=True)
            return None, None

    def _build_input_state(self, request: ChatRequest, session_id: str) -> dict[str, Any]:
        """
        @desc Xây dựng dictionary trạng thái đầu vào ban đầu cho LangGraph dựa trên yêu cầu và session
        @params request (ChatRequest): Đối tượng yêu cầu chat từ người dùng
        @params session_id (str): ID phiên hội thoại hiện tại
        @return dict[str, Any]: Dictionary trạng thái đầu vào dùng để khởi động pipeline graph
        """
        return {
            "messages": [HumanMessage(content=request.message)],
            "session_metadata": {
                "session_id": session_id,
                "channel": request.channel,
                "user_id": request.user_id,
                "timestamp": time.time(),
            },
            "iteration_count": 0,
            "retrieved_products": [],
            "retrieval_scores": [],
            "budget_relaxed": False,
            "final_response": "",
            "error_state": None,
        }

    async def stream_chat(
        self, request: ChatRequest
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        @desc Xử lý yêu cầu chat theo chế độ streaming — sinh ra từng token từ Synth Agent và cuối cùng trả về metadata phiên hội thoại
        @params request (ChatRequest): Đối tượng yêu cầu chat từ người dùng
        @return AsyncGenerator[dict[str, Any], None]: Generator bất đồng bộ sinh ra dict {"token": str, "done": False} cho mỗi chunk và dict tổng kết ở cuối
        """
        session_id = request.session_id or str(uuid.uuid4())
        custom_logger.info(
            f"[ChatService] stream_chat | session={session_id} | channel={request.channel}"
        )

        graph = await get_compiled_graph()
        input_state = self._build_input_state(request, session_id)
        config = {"configurable": {"thread_id": session_id}}

        t0 = time.perf_counter()
        synth_chunks: list[str] = []
        final_state: dict[str, Any] = {}

        try:
            async for event in graph.astream_events(input_state, config=config, version="v2"):
                kind = event.get("event", "")
                node = event.get("metadata", {}).get("langgraph_node", "")

                if kind == "on_chat_model_stream" and node == "synth_agent":
                    chunk = event.get("data", {}).get("chunk")
                    token = getattr(chunk, "content", "") if chunk else ""
                    if token:
                        synth_chunks.append(token)
                        yield {"token": token, "done": False}

                elif kind == "on_chain_end" and event.get("name") == "LangGraph":
                    # Root graph completion — capture final state
                    output = event.get("data", {}).get("output", {})
                    if isinstance(output, dict):
                        final_state = output

        except Exception as exc:
            custom_logger.error(
                f"[ChatService] stream_chat error | session={session_id} | error={exc}",
                exc_info=True,
            )
            yield {"error": str(exc), "done": True}
            return

        latency_ms = (time.perf_counter() - t0) * 1000
        final_response = "".join(synth_chunks) or final_state.get("final_response", "")
        psych_state = final_state.get("psych_state")
        psych_confidence = final_state.get("psych_confidence") or 0.0
        primary_concern = final_state.get("primary_concern")
        consult_strategy = final_state.get("consult_strategy")
        iteration_count = final_state.get("iteration_count", 0)
        retrieved_products = final_state.get("retrieved_products", [])
        retrieval_scores = final_state.get("retrieval_scores", [])
        previous_turn_products = final_state.get("previous_turn_products", [])
        extracted_info = final_state.get("extracted_info")
        product_count = len(retrieved_products)

        custom_logger.info(
            f"[ChatService] stream_chat complete | session={session_id} | "
            f"latency={latency_ms:.0f}ms | tokens={len(synth_chunks)} | psych={psych_state}"
        )

        # Cùng side-effects với handle_chat (persist, tạo order nếu đủ điều kiện, business logs/ChromaDB)
        # — trước đây stream_chat chỉ persist tin nhắn, bỏ sót toàn bộ phần này.
        final_response = await self._post_process_turn(
            session_id=session_id,
            request=request,
            final_response=final_response,
            psych_state=psych_state,
            psych_confidence=psych_confidence,
            primary_concern=primary_concern,
            consult_strategy=consult_strategy,
            iteration_count=iteration_count,
            retrieved_products=retrieved_products,
            retrieval_scores=retrieval_scores,
            extracted_info=extracted_info,
            result_messages=final_state.get("messages", []),
            latency_ms=latency_ms,
        )

        image_urls = await self._resolve_product_images(
            extracted_info, retrieved_products, previous_turn_products, psych_state
        )

        yield {
            "done": True,
            "session_id": session_id,
            "response": final_response,
            "psych_state": psych_state.value if psych_state else None,
            "psych_confidence": psych_confidence,
            "consult_strategy": consult_strategy,
            "retrieved_product_count": product_count,
            "latency_ms": round(latency_ms, 2),
            "iteration_count": iteration_count,
            "image_urls": image_urls,
        }

    async def _persist_turn_async(
        self,
        session_id: str,
        user_id: int | None,
        channel: str,
        user_message: str,
        assistant_response: str,
        psych_state: str | None,
        consult_strategy: str | None,
        iteration_count: int,
        latency_ms: int,
    ) -> None:
        """
        @desc Gói bất đồng bộ cho _persist_turn — chạy lưu trữ hội thoại trên thread riêng để không chặn event loop
        @params session_id (str): ID phiên hội thoại cần lưu
        @params user_id (int | None): ID người dùng hoặc None nếu là khách
        @params channel (str): Kênh giao tiếp (web, mobile, v.v.)
        @params user_message (str): Nội dung tin nhắn của người dùng
        @params assistant_response (str): Nội dung phản hồi của trợ lý
        @params psych_state (str | None): Trạng thái tâm lý được phân tích
        @params consult_strategy (str | None): Chiến lược tư vấn được chọn
        @params iteration_count (int): Số vòng lặp xử lý của graph
        @params latency_ms (int): Độ trễ xử lý tính bằng mili giây
        """
        try:
            await run_with_deadlock_retry(
                self._persist_turn,
                session_id, user_id, channel,
                user_message, assistant_response,
                psych_state, consult_strategy,
                iteration_count, latency_ms,
            )
        except Exception as exc:
            custom_logger.warning(f"[ChatService] DB persist failed | session={session_id} | error={exc}")

    def _persist_turn(
        self,
        session_id: str,
        user_id: int | None,
        channel: str,
        user_message: str,
        assistant_response: str,
        psych_state: str | None,
        consult_strategy: str | None,
        iteration_count: int,
        latency_ms: int,
    ) -> None:
        """
        @desc Lưu lượt hội thoại vào cơ sở dữ liệu — upsert session, ghi tin nhắn người dùng và trợ lý, cập nhật trạng thái phiên
        @params session_id (str): ID phiên hội thoại cần lưu
        @params user_id (int | None): ID người dùng hoặc None nếu là khách
        @params channel (str): Kênh giao tiếp
        @params user_message (str): Nội dung tin nhắn của người dùng
        @params assistant_response (str): Nội dung phản hồi của trợ lý
        @params psych_state (str | None): Trạng thái tâm lý được phân tích
        @params consult_strategy (str | None): Chiến lược tư vấn được chọn
        @params iteration_count (int): Số vòng lặp xử lý của graph
        @params latency_ms (int): Độ trễ xử lý tính bằng mili giây
        """
        with get_db() as db:
            repo = ConversationRepository(db)
            session = repo.upsert_session(session_id, user_id, channel)
            turn_number = (session.total_turns or 0) + 1

            repo.log_message(
                session_id=session.id,
                turn_number=turn_number,
                role="user",
                content=user_message,
            )
            repo.log_message(
                session_id=session.id,
                turn_number=turn_number,
                role="assistant",
                content=assistant_response,
                agent_name="synth_agent",
                latency_ms=latency_ms,
            )
            repo.update_session_after_turn(
                session=session,
                psych_state=psych_state,
                consult_strategy=consult_strategy,
                iteration_count=iteration_count,
            )
            custom_logger.info(
                f"[ChatService] turn persisted | session={session_id} | "
                f"turn={turn_number} | psych={psych_state} | latency={latency_ms}ms"
            )
