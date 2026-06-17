"""
Kafka topic constants — tập trung tại đây để tránh magic strings.

Topic naming convention: {project}.{domain}.{event}

TOPIC_BOT_INCOMING  — mọi tin nhắn đến từ tất cả platforms/bots
                       key   = session_key ("{platform}:{bot}:{sender}")
                       → cùng user luôn đi vào cùng partition → xử lý theo thứ tự

TOPIC_BOT_DLQ       — dead letter queue: tin nhắn thất bại sau max retries
                       Consumer sau đó có thể alert, replay, hoặc discard.
"""

TOPIC_BOT_INCOMING = "pancharm.bot.messages.incoming"
TOPIC_BOT_DLQ = "pancharm.bot.messages.dlq"
