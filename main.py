import warnings
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.api_router import api_router
from core.config import settings
from core.logger import custom_logger
from exceptions.global_exception_handler import register_exception_handler

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    custom_logger.info("Initializing Pancharm MAS — pre-warming LangGraph graph...")
    try:
        from graph.graph import get_compiled_graph
        get_compiled_graph()
        custom_logger.info("LangGraph graph compiled and ready.")
    except Exception as exc:
        custom_logger.warning(f"Graph pre-warm failed (non-fatal): {exc}")
    yield
    custom_logger.info("Shutting down Pancharm MAS.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=settings.APP_DESCRIPTION,
    lifespan=lifespan,
)

# CORS — restricted to approved retail partner domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")

register_exception_handler(app=app)

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
