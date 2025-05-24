import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi_pagination import add_pagination

from app.db import create_table
from app.exceptions import request_validation_exception_handler
from app.routes import router as api
from app.worker import scan_video

CURRENT_DIR = Path(__file__).resolve().parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_table()

    load_dotenv(dotenv_path=CURRENT_DIR.parent / ".env", verbose=True)

    scan_task = asyncio.create_task(scan_video())

    yield

    scan_task.cancel()


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(CURRENT_DIR / "static")), name="static")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_headers=["*"],
    allow_methods=["*"],
)
app.include_router(api)
add_pagination(app)

app.add_exception_handler(RequestValidationError, request_validation_exception_handler)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8080)
