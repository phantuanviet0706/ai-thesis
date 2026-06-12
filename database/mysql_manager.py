from core.config import settings
from database.database import DatabaseSettings, DBManager


class MySQLConfig(DatabaseSettings):
    db_type: str = "mysql+pymysql"
    db_host: str = settings.DB_HOST
    db_port: int = settings.DB_PORT
    db_name: str = settings.DB_NAME
    db_user: str = settings.DB_USER
    db_password: str = settings.DB_PASSWORD
    pool_size: int = settings.DB_POOL_SIZE
    max_overflow: int = settings.DB_MAX_OVERFLOW


class MySQLManager:
    @staticmethod
    def init():
        """
        @desc Khởi tạo kết nối MySQL bằng cách đăng ký engine và session factory vào DBManager
        """
        config = MySQLConfig()
        DBManager.register_db(
            db_key="mysql",
            config=config,
            pool_recycle=3600,
        )

    @staticmethod
    def get_db():
        """
        @desc Tạo và cung cấp phiên làm việc MySQL dùng cho dependency injection trong FastAPI
        @return Session: Đối tượng phiên SQLAlchemy kết nối tới MySQL
        """
        with DBManager.get_db_session("mysql") as session:
            yield session


mysql_manager = MySQLManager()
