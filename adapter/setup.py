from adapter.messenger_adapter import MessengerAdapter
from adapter.registry import AdapterRegistry
from adapter.telegram_adapter import TelegramAdapter
from adapter.zalo_adapter import ZaloAdapter
from core.config import settings
from core.logger import custom_logger


async def setup_adapters() -> None:
    """
    Đăng ký adapter cho Telegram, Messenger, Zalo dựa vào token đã cấu hình trong .env.
    Sau đó gọi register() trên từng adapter để đăng ký webhook với platform.
    """
    if settings.TELEGRAM_BOT_TOKEN:
        AdapterRegistry.register(TelegramAdapter())

    if settings.MESSENGER_PAGE_ACCESS_TOKEN:
        AdapterRegistry.register(MessengerAdapter())

    if settings.ZALO_OA_ACCESS_TOKEN:
        AdapterRegistry.register(ZaloAdapter())

    registered = AdapterRegistry.list_registered()
    custom_logger.info(
        f"[AdapterSetup] {len(registered)} adapter(s) loaded | "
        + (", ".join(f"{a['platform']}:{a['bot_name']}" for a in registered) or "none")
    )

    for info in registered:
        adapter = AdapterRegistry.get(info["platform"], info["bot_name"])
        if adapter:
            try:
                await adapter.register()
            except Exception as exc:
                custom_logger.warning(
                    f"[AdapterSetup] register() failed for "
                    f"{info['platform']}:{info['bot_name']} — {exc}"
                )
