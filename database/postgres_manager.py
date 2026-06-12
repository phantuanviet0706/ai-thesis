from core.config import settings
from database.database import DBManager, DatabaseSettings


class PostgresConfig(DatabaseSettings):
    db_type: str = "postgresql+psycopg2"
    db_host: str = settings.PG_HOST
    db_port: int = settings.PG_PORT
    db_name: str = settings.PG_NAME
    db_user: str = settings.PG_USER
    db_password: str = settings.PG_PASSWORD
    pool_size: int = settings.PG_POOL_SIZE
    max_overflow: int = settings.PG_MAX_OVERFLOW


@DBManager.register_manager
class PostgresManager:
    @staticmethod
    def init():
        """
        @desc Khởi tạo kết nối PostgreSQL bằng cách đăng ký engine và session factory cho cả khóa "default" và "postgres"
        """
        config = PostgresConfig()
        DBManager.register_db(db_key="default", config=config)
        DBManager.register_db(db_key="postgres", config=config)

    @staticmethod
    def get_db():
        """
        @desc Tạo và cung cấp phiên làm việc PostgreSQL dùng cho dependency injection trong FastAPI
        @return Session: Đối tượng phiên SQLAlchemy kết nối tới PostgreSQL
        """
        with DBManager.get_db_session("postgres") as session:
            yield session


postgres_manager = PostgresManager()
