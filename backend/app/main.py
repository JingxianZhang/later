from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .db import db
from .api import router as api_router
from .telegram import router as tg_router
app = FastAPI(title="Later API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup() -> None:
    await db.connect()


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await db.disconnect()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "env": settings.environment}


app.include_router(api_router, prefix="/v1")
app.include_router(tg_router, prefix="/v1")

