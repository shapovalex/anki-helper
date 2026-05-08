# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Run the development server:**
```bash
uv run uvicorn app.main:app --reload
```

**Install dependencies:**
```bash
uv sync
```

## Architecture

This is a FastAPI web application intended to integrate with Anki via the Anki Connect HTTP API.

- `app/main.py` — FastAPI app entry point; mounts `static/` and serves `static/index.html` at `/`
- `static/index.html` — Frontend UI
- Python 3.13, managed with `uv`

## Anki Connect

Anki Connect documentation: https://git.sr.ht/~foosoft/anki-connect

Anki Connect runs as a local HTTP server (default port 8765) inside the Anki desktop app. All Anki operations (deck management, card creation, querying) go through POST requests to `http://localhost:8765` with a JSON body of `{"action": "...", "version": 6, "params": {...}}`.
