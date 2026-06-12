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
        """
        @desc Tạo chuỗi kết nối URL cho cơ sở dữ liệu dựa trên các thông số cấu hình
        @return str: Chuỗi URL kết nối theo định dạng SQLAlchemy
        """
        return f"{self.db_type}://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"


class DBManager:
    _engines: Dict[str, Any] = {}
    _session_factories: Dict[str, sessionmaker] = {}
    _registered_managers: List[Any] = []

    @classmethod
    def register_manager(cls, manager_class):
        """
        @desc Đăng ký một lớp quản lý cơ sở dữ liệu con vào danh sách quản lý của factory
        @params manager_class (type): Lớp quản lý cần đăng ký
        @return type: Lớp quản lý vừa được đăng ký (để dùng như decorator)
        """
        cls._registered_managers.append(manager_class)
        return manager_class

    @classmethod
    def init_all(cls):
        """
        @desc Khởi tạo tất cả các cơ sở dữ liệu đã đăng ký bằng cách gọi phương thức init() trên từng manager
        """
        from core.logger import custom_logger
        for manager in cls._registered_managers:
            manager.init()
        custom_logger.info(f"[DBManager] All {len(cls._registered_managers)} databases initialized")

    @classmethod
    def register_db(cls, db_key: str, config: DatabaseSettings, **extra_kwargs):
        """
        @desc Tạo và đăng ký engine cùng session factory cho một kết nối cơ sở dữ liệu theo khóa định danh
        @params db_key (str): Khóa định danh duy nhất cho kết nối cơ sở dữ liệu
        @params config (DatabaseSettings): Đối tượng cấu hình chứa thông tin kết nối
        @params extra_kwargs (dict): Các tham số bổ sung truyền thêm vào hàm create_engine
        """
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
        """
        @desc Cung cấp một phiên làm việc với cơ sở dữ liệu theo dạng context manager, tự động commit hoặc rollback
        @params db_key (str): Khóa định danh của cơ sở dữ liệu cần lấy phiên, mặc định là "default"
        @return Session: Đối tượng phiên SQLAlchemy để thực hiện các thao tác với cơ sở dữ liệu
        """
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
