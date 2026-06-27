import warnings
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from adapter.setup import setup_adapters
from api.api_router import api_router
from core.config import settings
from core.logger import custom_logger
from database.database import DBManager
import database.mysql_manager  # noqa: F401 — registers MySQLManager via @DBManager.register_manager
from exceptions.global_exception_handler import register_exception_handler
from graph.graph import get_compiled_graph
from messaging.consumer import BotMessageConsumer
from messaging.producer import bot_producer
from middleware.rate_limit_middleware import RateLimitMiddleware

load_dotenv()

_bot_consumer = BotMessageConsumer()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Databases
    DBManager.init_all()
    custom_logger.info("Databases initialized.")

    # 2. LangGraph graph (pre-warm)
    custom_logger.info("Initializing Pancharm MAS — pre-warming LangGraph graph...")
    try:
        await get_compiled_graph()
        custom_logger.info("LangGraph graph compiled and ready.")
    except Exception as exc:
        custom_logger.warning(f"Graph pre-warm failed (non-fatal): {exc}")

    # 3. Platform adapters (register bots + webhook URLs)
    await setup_adapters()

    # 4. Kafka producer + consumer
    if settings.KAFKA_BOOTSTRAP_SERVERS:
        try:
            await bot_producer.start()
            await _bot_consumer.start()
            custom_logger.info("Kafka producer and consumer started.")
        except Exception as exc:
            custom_logger.warning(
                f"Kafka unavailable — bot messaging disabled: {exc}"
            )

    yield

    # Graceful shutdown
    await _bot_consumer.stop()
    await bot_producer.stop()
    custom_logger.info("Shutting down Pancharm MAS.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=settings.APP_DESCRIPTION,
    lifespan=lifespan,
    redirect_slashes=False,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RateLimitMiddleware)

app.include_router(api_router, prefix="/api/v1")

register_exception_handler(app=app)

warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message=".*pkg_resources is deprecated.*")


@app.get("/")
def root():
    return {
        "message": settings.APP_DESCRIPTION,
        "version": settings.APP_VERSION,
        "architecture": "4-agent MAS (Orchestrator + KR + Psych + Synth)",
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}
