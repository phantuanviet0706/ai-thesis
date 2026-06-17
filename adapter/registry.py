"""
AdapterRegistry — central registry for all active platform adapter instances.

Maps "{platform}:{bot_name}" → BaseAdapter so webhook controllers can route
incoming requests to the correct adapter without hardcoding.

Supports:
  - Multiple platforms: telegram, zalo, facebook, line, ...
  - Multiple bots per platform: pancharm, affiliate, support, ...

Usage:
    # At startup — called from adapter/setup.py:
    AdapterRegistry.register(TelegramAdapter())

    # In webhook controller:
    adapter = AdapterRegistry.get("telegram", bot_name)
    if not adapter:
        raise HTTPException(404, "Bot not found")
"""

from adapter.base_adapter import BaseAdapter
from core.logger import custom_logger


class AdapterRegistry:
    _registry: dict[str, BaseAdapter] = {}

    @classmethod
    def register(cls, adapter: BaseAdapter) -> None:
        """Register an adapter instance. Overwrites any existing entry for the same key."""
        key = cls._key(adapter.platform, adapter.bot_name)
        cls._registry[key] = adapter
        custom_logger.info(
            f"[AdapterRegistry] registered | platform={adapter.platform} | "
            f"bot={adapter.bot_name} | key={key}"
        )

    @classmethod
    def get(cls, platform: str, bot_name: str) -> BaseAdapter | None:
        """Retrieve adapter by platform + bot_name. Returns None if not registered."""
        return cls._registry.get(cls._key(platform, bot_name))

    @classmethod
    def get_or_raise(cls, platform: str, bot_name: str) -> BaseAdapter:
        """
        Retrieve adapter by platform + bot_name.
        Raises KeyError if not registered — use in webhook handlers.
        """
        adapter = cls.get(platform, bot_name)
        if adapter is None:
            raise KeyError(
                f"No adapter registered for platform='{platform}', bot='{bot_name}'. "
                f"Registered: {list(cls._registry.keys())}"
            )
        return adapter

    @classmethod
    def list_registered(cls) -> list[dict[str, str]]:
        """Return all registered adapters as a list of {platform, bot_name} dicts."""
        return [
            {"platform": adapter.platform, "bot_name": adapter.bot_name}
            for adapter in cls._registry.values()
        ]

    @classmethod
    def unregister(cls, platform: str, bot_name: str) -> None:
        key = cls._key(platform, bot_name)
        cls._registry.pop(key, None)
        custom_logger.info(f"[AdapterRegistry] unregistered | key={key}")

    @classmethod
    def _key(cls, platform: str, bot_name: str) -> str:
        return f"{platform}:{bot_name}"
