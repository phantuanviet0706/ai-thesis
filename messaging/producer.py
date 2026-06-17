"""
BotMessageProducer — publish StandardMessage lên Kafka topic thông qua KafkaManager.

KafkaManager dùng kafka-python (đồng bộ) → mọi lệnh gửi được wrap trong
asyncio.to_thread để không block event loop của FastAPI.
Webhook controller gọi producer.publish() sau khi parse xong payload,
nhờ đó trả về 200 OK ngay mà không chờ MAS xử lý.

Fallback: nếu Kafka không kết nối được khi start() → is_ready = False
→ WebhookController tự chuyển sang direct BackgroundTask processing.

Partition strategy:
    key = session_key ("telegram:pancharm:123456")
    → cùng user luôn vào cùng partition → đảm bảo thứ tự tin nhắn
"""

import asyncio

from core.logger import custom_logger
from infrastructure.kafka_client import kafka_manager
from messaging.topics import TOPIC_BOT_INCOMING
from schemas.standard_message import StandardMessage


class BotMessageProducer:

    def __init__(self) -> None:
        self._ready = False

    async def start(self) -> None:
        try:
            await asyncio.to_thread(lambda: kafka_manager.producer)
            self._ready = True
            custom_logger.info(
                f"[BotMessageProducer] started via KafkaManager | "
                f"brokers={kafka_manager._bootstrap_servers}"
            )
        except Exception as exc:
            self._ready = False
            custom_logger.warning(
                f"[BotMessageProducer] Kafka connection failed — running without Kafka: {exc}"
            )

    async def stop(self) -> None:
        if self._ready:
            await asyncio.to_thread(kafka_manager.close)
        self._ready = False
        custom_logger.info("[BotMessageProducer] stopped")

    @property
    def is_ready(self) -> bool:
        """True nếu Kafka đang kết nối và sẵn sàng nhận message."""
        return self._ready

    async def publish(self, msg: StandardMessage) -> None:
        """
        Publish một StandardMessage vào Kafka topic.
        Dùng session_key làm partition key để đảm bảo ordering per user.
        Raise RuntimeError nếu producer chưa sẵn sàng — caller nên kiểm tra is_ready trước.
        """
        if not self._ready:
            raise RuntimeError(
                "[BotMessageProducer] producer chưa sẵn sàng. Kiểm tra is_ready trước khi publish."
            )

        await asyncio.to_thread(
            kafka_manager.send_message,
            TOPIC_BOT_INCOMING,
            msg.model_dump(),
            msg.session_key,
        )
        custom_logger.info(
            f"[BotMessageProducer] published | topic={TOPIC_BOT_INCOMING} | "
            f"key={msg.session_key} | msg='{msg.message[:60]}'"
        )


# Singleton — khởi tạo một lần, import ở mọi nơi cần dùng
bot_producer = BotMessageProducer()
