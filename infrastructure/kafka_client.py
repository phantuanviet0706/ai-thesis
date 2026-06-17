import json
from typing import Optional

from kafka import KafkaConsumer, KafkaProducer

from core.config import settings
from core.logger import custom_logger


class KafkaManager:

    def __init__(self):
        self._bootstrap_servers = settings.KAFKA_BOOTSTRAP_SERVERS
        self._client_id = settings.KAFKA_CLIENT_ID
        self._producer: Optional[KafkaProducer] = None

    @property
    def producer(self) -> KafkaProducer:
        """Lazy singleton — kết nối lần đầu khi gọi, raise nếu broker không sẵn sàng."""
        if self._producer is None:
            self._producer = KafkaProducer(
                bootstrap_servers=self._bootstrap_servers,
                client_id=self._client_id,
                value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
                acks="all",
            )
        return self._producer

    def send_message(self, topic: str, data: dict, key: Optional[str] = None) -> None:
        """
        Gửi JSON message lên Kafka topic. Đồng bộ (blocking) — gọi từ asyncio.to_thread
        khi dùng trong code async để không block event loop.
        """
        future = self.producer.send(topic, value=data, key=key)
        future.add_callback(self._on_delivery_success, topic)
        future.add_errback(self._on_delivery_error, topic)
        self.producer.flush()

    def create_consumer(self, group_id: str, topics: list[str]) -> KafkaConsumer:
        """
        Tạo consumer mới cho worker xử lý task.
        KafkaConsumer trả về là iterator đồng bộ (blocking) — caller chịu trách nhiệm
        chạy trong thread riêng và đóng consumer khi xong.
        """
        return KafkaConsumer(
            *topics,
            bootstrap_servers=self._bootstrap_servers,
            client_id=self._client_id,
            group_id=group_id,
            auto_offset_reset="earliest",
            enable_auto_commit=False,
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            key_deserializer=lambda k: k.decode("utf-8") if k else None,
        )

    def close(self) -> None:
        if self._producer is not None:
            self._producer.close()
            self._producer = None

    # ── Callbacks ─────────────────────────────────────────────────────────────

    def _on_delivery_success(self, topic: str, record_metadata) -> None:
        custom_logger.info(
            f"[KafkaManager] delivered | topic={topic} | "
            f"partition={record_metadata.partition} | offset={record_metadata.offset}"
        )

    def _on_delivery_error(self, topic: str, exc: Exception) -> None:
        custom_logger.error(f"[KafkaManager] delivery failed | topic={topic} | error={exc}")


kafka_manager = KafkaManager()
