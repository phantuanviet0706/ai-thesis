"""
BotMessageConsumer — lắng nghe Kafka topic (qua KafkaManager) và điều phối xử lý đến từng bot.

KafkaConsumer của kafka-python là iterator đồng bộ (blocking) → vòng lặp tiêu thụ
chạy trong thread riêng (asyncio.to_thread). Mỗi message nhận được được đẩy ngược
vào event loop chính bằng asyncio.run_coroutine_threadsafe(...).result() để xử lý
async (gọi MAS pipeline, gửi response) — block thread tiêu thụ cho tới khi xử lý
xong, qua đó giữ đúng thứ tự message trong cùng partition.

Retry strategy:
    - Thử lại tối đa MAX_RETRIES lần với backoff tăng dần
    - Sau khi hết retry → publish vào DLQ và commit offset (skip)

Fallback: nếu Kafka không kết nối được khi start() → consumer disabled, log warning.
Trong trường hợp đó, WebhookController dùng BackgroundTask trực tiếp.
"""

import asyncio
import time
from typing import Optional

from core.config import settings
from core.logger import custom_logger
from infrastructure.kafka_client import kafka_manager
from messaging.handler import handle_message
from messaging.topics import TOPIC_BOT_DLQ, TOPIC_BOT_INCOMING
from schemas.standard_message import StandardMessage

_MAX_RETRIES = 3
_RETRY_BACKOFF = [1.0, 2.0, 4.0]   # seconds per attempt


class BotMessageConsumer:

    def __init__(self) -> None:
        self._consumer = None
        self._running = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        try:
            self._consumer = await asyncio.to_thread(
                kafka_manager.create_consumer,
                settings.KAFKA_CONSUMER_GROUP,
                [TOPIC_BOT_INCOMING],
            )
        except Exception as exc:
            custom_logger.warning(
                f"[BotMessageConsumer] Kafka connection failed — consumer disabled: {exc}"
            )
            self._consumer = None
            return

        self._running = True
        self._loop = asyncio.get_running_loop()
        self._task = asyncio.create_task(
            asyncio.to_thread(self._consume_loop),
            name="bot-message-consumer",
        )
        custom_logger.info(
            f"[BotMessageConsumer] started | "
            f"topic={TOPIC_BOT_INCOMING} | group={settings.KAFKA_CONSUMER_GROUP}"
        )

    async def stop(self) -> None:
        self._running = False
        if self._consumer:
            await asyncio.to_thread(self._consumer.close)
        if self._task:
            try:
                await self._task
            except Exception:
                pass
        custom_logger.info("[BotMessageConsumer] stopped")

    # ── Main loop — chạy trong thread riêng ─────────────────────────────────────

    def _consume_loop(self) -> None:
        for record in self._consumer:
            if not self._running:
                break

            success = False
            last_error: Optional[Exception] = None

            for attempt in range(_MAX_RETRIES):
                try:
                    self._dispatch(record)
                    success = True
                    break
                except Exception as exc:
                    last_error = exc
                    wait = _RETRY_BACKOFF[attempt]
                    custom_logger.warning(
                        f"[BotMessageConsumer] attempt {attempt + 1}/{_MAX_RETRIES} failed | "
                        f"key={record.key} | error={exc} | retry in {wait}s"
                    )
                    time.sleep(wait)

            if not success:
                custom_logger.error(
                    f"[BotMessageConsumer] max retries exceeded | "
                    f"key={record.key} | sending to DLQ | error={last_error}"
                )
                self._publish_dlq(record, str(last_error))

            self._consumer.commit()

    # ── Dispatch ──────────────────────────────────────────────────────────────

    def _dispatch(self, record) -> None:
        data: dict = record.value
        std_msg = StandardMessage(**data)

        custom_logger.info(
            f"[BotMessageConsumer] dispatching | "
            f"platform={std_msg.platform} | bot={std_msg.bot_name} | "
            f"sender={std_msg.sender_id} | msg='{std_msg.message[:80]}'"
        )

        future = asyncio.run_coroutine_threadsafe(handle_message(std_msg), self._loop)
        future.result()

    # ── DLQ ──────────────────────────────────────────────────────────────────

    def _publish_dlq(self, record, error: str) -> None:
        payload = {
            "original": record.value,
            "error": error,
            "topic": record.topic,
            "partition": record.partition,
            "offset": record.offset,
        }
        try:
            kafka_manager.send_message(TOPIC_BOT_DLQ, payload, key=record.key)
            custom_logger.info(f"[BotMessageConsumer] DLQ published | key={record.key}")
        except Exception as exc:
            custom_logger.error(f"[BotMessageConsumer] DLQ publish failed | error={exc}")
