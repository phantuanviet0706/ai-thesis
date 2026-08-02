from logging.config import fileConfig
from urllib.parse import quote_plus

from alembic import context
from sqlalchemy import create_engine, pool

from core.config import settings
import entity  # noqa: F401 — populates entity.base_model.Base.metadata for autogenerate
from entity.base_model import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# quote_plus bắt buộc — xem ghi chú trong database/__init__.py::DATABASE_URL
DATABASE_URL = (
    f"mysql+pymysql://{quote_plus(settings.DB_USER)}:{quote_plus(settings.DB_PASSWORD)}"
    f"@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
    f"?charset=utf8mb4"
)
# KHÔNG dùng config.set_main_option("sqlalchemy.url", DATABASE_URL) — ConfigParser coi "%"
# là ký tự interpolation (%(name)s), nên URL đã quote_plus (chứa vd "%40") làm nó ném
# ValueError "invalid interpolation syntax". Engine được tạo trực tiếp từ DATABASE_URL trong
# run_migrations_online()/run_migrations_offline() bên dưới, không đi qua configparser.


def run_migrations_offline() -> None:
    """Generate SQL script without a live DB connection (`alembic upgrade head --sql`)."""
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Connect to MySQL and apply migrations directly — the normal path (`alembic upgrade head`)."""
    connectable = create_engine(DATABASE_URL, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
