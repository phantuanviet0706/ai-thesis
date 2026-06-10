from contextlib import contextmanager
from typing import Any, Dict, List

from pydantic_settings import BaseSettings
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


class DatabaseSettings(BaseSettings):
    db_type: str
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str
    pool_size: int
    max_overflow: int

    @property
    def database_url(self) -> str:
        return f"{self.db_type}://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"


class DBManager:
    _engines: Dict[str, Any] = {}
    _session_factories: Dict[str, sessionmaker] = {}
    _registered_managers: List[Any] = []

    @classmethod
    def register_manager(cls, manager_class):
        """Register a sub-manager into the factory."""
        cls._registered_managers.append(manager_class)
        return manager_class

    @classmethod
    def init_all(cls):
        """FACTORY INIT: Call init() on all registered managers."""
        for manager in cls._registered_managers:
            manager.init()
        print(f"--- All {len(cls._registered_managers)} databases initialized ---")

    @classmethod
    def register_db(cls, db_key: str, config: DatabaseSettings, **extra_kwargs):
        if db_key not in cls._engines:
            engine = create_engine(
                config.database_url,
                pool_size=config.pool_size,
                max_overflow=config.max_overflow,
                pool_pre_ping=True,
                **extra_kwargs,
            )
            cls._engines[db_key] = engine
            cls._session_factories[db_key] = sessionmaker(
                bind=engine,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False,
            )

    @classmethod
    @contextmanager
    def get_db_session(cls, db_key: str = "default") -> Session:
        if db_key not in cls._session_factories:
            raise ValueError(f"Database key '{db_key}' is not registered.")
        session = cls._session_factories[db_key]()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
