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
        config = PostgresConfig()
        DBManager.register_db(
            db_key="postgres",
            config=config,
        )

    @staticmethod
    def get_db():
        with DBManager.get_db_session("postgres") as session:
            yield session


postgres_manager = PostgresManager()
