from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.anki_client import AnkiClient
from app.routers import decks as decks_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with httpx.AsyncClient(timeout=10.0) as http_client:
        app.state.anki_client = AnkiClient(http_client)
        yield


app = FastAPI(title="Anki Helper", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(decks_router.router)


@app.get("/")
async def index() -> FileResponse:
    return FileResponse("static/index.html")


@app.get("/decks")
async def decks() -> FileResponse:
    return FileResponse("static/decks.html")
