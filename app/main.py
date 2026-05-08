from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.anki_client import AnkiClient
from app.config import ConfigManager
from app.routers import decks as decks_router
from app.routers import pronunciation as pronunciation_router
from app.routers import settings as settings_router
from app.routers import word_lookup as word_lookup_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with httpx.AsyncClient(timeout=10.0) as http_client:
        app.state.config = ConfigManager()
        app.state.http_client = http_client
        app.state.anki_client = AnkiClient(http_client)
        yield


app = FastAPI(title="Anki Helper", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(decks_router.router)
app.include_router(pronunciation_router.router)
app.include_router(settings_router.router)
app.include_router(word_lookup_router.router)


@app.get("/")
async def index() -> FileResponse:
    return FileResponse("static/index.html")


@app.get("/word-lookup")
async def word_lookup() -> FileResponse:
    return FileResponse("static/word-lookup.html")


@app.get("/settings")
async def settings() -> FileResponse:
    return FileResponse("static/settings.html")


@app.get("/help")
async def help_page() -> FileResponse:
    return FileResponse("static/help.html")
