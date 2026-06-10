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


@DBManager.register_manager
class MySQLManager:
    @staticmethod
    def init():
        config = MySQLConfig()
        DBManager.register_db(
            db_key="mysql",
            config=config,
            pool_recycle=3600,
        )

    @staticmethod
    def get_db():
        with DBManager.get_db_session("mysql") as session:
            yield session


mysql_manager = MySQLManager()
