from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        print("Initialize Data")
    except Exception as e:
        print(f"Initialize error: {e}")
    yield

app = FastAPI()

# app.include_router(api_router, prefix="/api/v1")
#
# """Register Exception Handler"""
# register_exception_handler(app=app)
#
# """Ignore Warnings"""
# warnings.filterwarnings("ignore", category=DeprecationWarning)
# warnings.filterwarnings("ignore", message=".*pkg_resources is deprecated.*")

# @app.get("/")
# def root():
#     print("Request hit root endpoint!")
#     return {
#         "message": settings.APP_DESCRIPTION,
#         "version": settings.APP_VERSION,
#     }

@app.get("/health")
def health_check():
    return {"status": "healthy"}