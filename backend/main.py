"""
PolicyGraph-RAG backend entry point.

Run with: uvicorn main:app --reload --port 8000
"""
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api import auth, chat, graph, health, okf, patients, policies
from config import get_settings
from database.db import init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(
    title="PolicyGraph-RAG",
    description="Temporal, Contradiction-Aware and Evidence-Verified RAG for Healthcare Insurance Navigation",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def safe_error_handler(request: Request, exc: Exception):
    """Avoid leaking internals (stack traces, SQL, secrets) in error responses."""
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error."})


@app.on_event("startup")
async def on_startup():
    await init_db()
    logger.info("PolicyGraph-RAG backend started (env=%s)", settings.env)


app.include_router(health.router)
app.include_router(auth.router)
app.include_router(policies.router)
app.include_router(chat.router)
app.include_router(graph.router)
app.include_router(patients.router)
app.include_router(okf.router)

