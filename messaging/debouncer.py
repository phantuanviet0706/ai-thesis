"""
MessageDebouncer — gộp nhiều tin nhắn liên tiếp của cùng 1 khách trong 1 khoảng thời gian ngắn
(MESSAGE_DEBOUNCE_SECONDS) thành 1 lượt xử lý duy nhất.

Vấn đề: khách hàng thường gõ rời rạc nhiều tin nhắn ngắn thay vì 1 tin nhắn dài — vd "cho hỏi",
"vòng tay", "mệnh kim", "tầm 2 triệu" gửi thành 4 tin liên tiếp cách nhau vài giây. Nếu mỗi tin
nhắn kích hoạt riêng 1 lần chạy graph, hệ thống trả lời rời rạc/chồng chéo cho từng tin một —
"loạn" đúng như quan sát thực tế, thay vì gộp lại thành 1 câu hỏi hoàn chỉnh rồi trả lời 1 lần.

Cơ chế: mỗi tin nhắn mới đến của cùng session_key được nối vào buffer và RESET lại đồng hồ đếm
ngược MESSAGE_DEBOUNCE_SECONDS. Khi khách ngừng gửi tin trong đúng khoảng đó, buffer được gộp
thành 1 văn bản (nối bằng "\n") và gọi callback on_flush đúng 1 lần. Nếu tin mới tới trước khi hết
giờ, đồng hồ được gia hạn tiếp — quá trình lặp lại tới khi khách thực sự ngừng gõ.

An toàn concurrency: dùng asyncio.Lock bảo vệ thao tác đọc/ghi buffer + timer; hàm flush tự kiểm
tra "mình có còn là timer hiện hành của session này không" trước khi xử lý — tránh race hiếm khi
1 tin nhắn mới đến đúng lúc timer cũ vừa hết giờ (xem _flush_after_delay).

Xếp hàng khi đang xử lý (quan trọng): nếu khách gửi câu hỏi 2 trong lúc bot CHƯA trả lời xong câu
hỏi 1 (on_flush của câu 1 vẫn đang chạy — gọi LLM, tra cứu sản phẩm... có thể mất vài giây), câu
hỏi 2 vẫn được debounce bình thường và có đồng hồ riêng — nhưng khi tới lúc flush, nó phải CHỜ tới
khi on_flush của câu 1 chạy xong mới được chạy (per-session processing lock), KHÔNG chạy song song.
Lý do bắt buộc: 2 lượt gọi graph.ainvoke() đồng thời cho CÙNG 1 thread_id (session) sẽ tranh chấp
cùng 1 bản ghi checkpoint của LangGraph, có thể làm hỏng state hội thoại hoặc trả lời sai thứ tự.
Nhờ checkpointer lưu lại lịch sử đầy đủ, khi câu hỏi 2 tới lượt chạy, nó tự động thấy được cả câu
hỏi 1 LẪN câu trả lời bot vừa gửi — không cần xử lý gì thêm để "liên kết ngữ cảnh".
"""

import asyncio
from collections.abc import Awaitable, Callable

from constants.constants import MESSAGE_DEBOUNCE_SECONDS
from core.logger import custom_logger
from schemas.standard_message import StandardMessage

_FlushHandler = Callable[[StandardMessage], Awaitable[None]]


class MessageDebouncer:
    def __init__(self, delay_seconds: float = MESSAGE_DEBOUNCE_SECONDS) -> None:
        self._delay_seconds = delay_seconds
        self._buffers: dict[str, list[str]] = {}
        self._latest: dict[str, StandardMessage] = {}
        self._timers: dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()
        # 1 Lock riêng cho mỗi session — đảm bảo on_flush (chạy graph) không bao giờ chạy song
        # song cho cùng 1 khách, dù tồn tại suốt vòng đời process (không dọn theo session đã xong
        # — chấp nhận được vì Lock rỗng chiếm rất ít bộ nhớ, không đáng công dọn cho quy mô hệ thống này).
        self._processing_locks: dict[str, asyncio.Lock] = {}

    def _get_processing_lock(self, key: str) -> asyncio.Lock:
        lock = self._processing_locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            self._processing_locks[key] = lock
        return lock

    async def add(self, std_msg: StandardMessage, on_flush: _FlushHandler) -> None:
        """
        @desc Đưa 1 tin nhắn vào buffer của đúng session, gia hạn đồng hồ debounce — gọi lại
        hàm này cho MỌI tin nhắn text đến (không phải command), on_flush chỉ thật sự chạy khi
        khách ngừng gửi tin trong đủ delay_seconds.
        @params std_msg (StandardMessage): Tin nhắn vừa nhận từ platform
        @params on_flush (Callable): Coroutine nhận StandardMessage đã gộp, chạy đúng 1 lần khi flush
        """
        key = std_msg.session_key
        async with self._lock:
            self._buffers.setdefault(key, []).append(std_msg.message)
            self._latest[key] = std_msg

            old_timer = self._timers.get(key)
            if old_timer and not old_timer.done():
                old_timer.cancel()

            self._timers[key] = asyncio.create_task(
                self._flush_after_delay(key, on_flush),
                name=f"debounce-{key}",
            )

    async def _flush_after_delay(self, key: str, on_flush: _FlushHandler) -> None:
        try:
            await asyncio.sleep(self._delay_seconds)
        except asyncio.CancelledError:
            # Bị hủy vì có tin nhắn mới tới (add() gọi old_timer.cancel()) — đây là hành vi bình
            # thường của debounce (gia hạn đồng hồ), không phải lỗi. Timer mới sẽ tự flush sau.
            return

        async with self._lock:
            # Trường hợp hiếm: tin nhắn mới đến đúng lúc sleep() vừa hết hạn nhưng trước khi task
            # này kịp acquire lock — add() đã tạo timer MỚI cho key này rồi. Nhường lại cho timer
            # mới, tránh flush thiếu tin vừa tới hoặc flush trùng 2 lần.
            if self._timers.get(key) is not asyncio.current_task():
                return
            texts = self._buffers.pop(key, [])
            latest_msg = self._latest.pop(key, None)
            self._timers.pop(key, None)

        if not texts or latest_msg is None:
            return

        combined_text = "\n".join(t for t in texts if t.strip())
        combined_msg = latest_msg.model_copy(update={"message": combined_text})

        # Xếp hàng nếu lượt trước của CÙNG session vẫn đang chạy (khách hỏi câu 2 khi bot chưa
        # trả lời xong câu 1) — chờ tới khi lượt trước xong mới chạy, không bao giờ chạy song
        # song graph cho cùng 1 khách (xem docstring module).
        processing_lock = self._get_processing_lock(key)
        if processing_lock.locked():
            custom_logger.info(
                f"[MessageDebouncer] session={key} đang xử lý lượt trước — "
                f"xếp hàng chờ, sẽ chạy ngay khi lượt hiện tại xong"
            )

        async with processing_lock:
            custom_logger.info(
                f"[MessageDebouncer] flush | session={key} | merged={len(texts)} message(s) → "
                f"1 lượt xử lý | combined_len={len(combined_text)}"
            )
            try:
                await on_flush(combined_msg)
            except Exception as exc:
                custom_logger.error(
                    f"[MessageDebouncer] on_flush failed | session={key} | error={exc}",
                    exc_info=True,
                )


message_debouncer = MessageDebouncer()
