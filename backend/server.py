"""
NyayaBot API Server - Unified FastAPI + Webhook Telegram Bot
Hosts REST API, Web UI, and Telegram Webhook on a single web service.
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Optional, List, Dict
import numpy as np
from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from pydantic import BaseModel
import uvicorn

# Fix Windows Unicode output encoding
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# ===== CRITICAL: Load .env FIRST before anything else =====
BASE_DIR = Path(__file__).parent.parent
ENV_FILE = BASE_DIR / ".env"

from dotenv import load_dotenv
load_dotenv(ENV_FILE, override=False)

# Verify key loaded
_gemini_key = os.getenv("GEMINI_API_KEY", "")
_anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")

if _gemini_key and _gemini_key != "your_gemini_api_key_here":
    print(f"[OK] Gemini API key loaded: {_gemini_key[:15]}...")
elif _anthropic_key and _anthropic_key != "your_anthropic_api_key_here":
    print(f"[OK] Anthropic API key loaded: {_anthropic_key[:15]}...")
else:
    print("[WARNING] No AI API key found in .env!")
    print(f"   Add GEMINI_API_KEY=AIza... to: {ENV_FILE}")
    print("   Get a free key at: https://aistudio.google.com/apikey")

sys.path.insert(0, str(BASE_DIR))
from rag.engine import NyayaBotRAGEngine
from bot.telegram_bot import build_telegram_app, process_telegram_update

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="NyayaBot API", version="1.0.0", docs_url="/api/docs", redoc_url="/api/redoc")

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

frontend_path = BASE_DIR / "frontend"
engine: Optional[NyayaBotRAGEngine] = None
telegram_app = None
webhook_registered = False


@app.on_event("startup")
async def startup():
    global engine, telegram_app, webhook_registered
    logger.info("Initializing NyayaBot RAG Engine...")
    os.chdir(BASE_DIR)
    engine = NyayaBotRAGEngine(
        api_key=os.getenv("GEMINI_API_KEY") or os.getenv("ANTHROPIC_API_KEY"),
        vector_store_path=str(BASE_DIR / "data" / "faiss_index"),
        policies_dir=str(BASE_DIR / "data" / "policies")
    )
    logger.info("NyayaBot ready!")

    # Initialize Telegram Bot in Webhook mode
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if token and token != "your_telegram_bot_token_here":
        try:
            logger.info("Initializing Telegram Bot (Webhook Mode)...")
            telegram_app = build_telegram_app(token=token, rag_engine=engine)
            await telegram_app.initialize()
            await telegram_app.start()
            logger.info("[OK] Telegram Bot application started.")

            # Register webhook if URL is provided
            webhook_url = os.getenv("WEBHOOK_URL") or os.getenv("RENDER_EXTERNAL_URL")
            if webhook_url and webhook_url.strip():
                clean_url = webhook_url.strip().rstrip("/")
                if not clean_url.endswith("/api/telegram-webhook") and not clean_url.endswith("/telegram-webhook"):
                    clean_url += "/api/telegram-webhook"

                logger.info(f"Setting Telegram Webhook to: {clean_url}")
                await telegram_app.bot.set_webhook(url=clean_url)
                webhook_registered = True
                logger.info(f"[OK] Telegram Webhook registered successfully -> {clean_url}")
            else:
                logger.info(
                    "[INFO] Telegram bot initialized. Set WEBHOOK_URL=https://<your-app>.onrender.com "
                    "in Render environment to register webhook."
                )
        except Exception as e:
            logger.error(f"Failed to initialize Telegram Bot: {e}", exc_info=True)
    else:
        logger.info("[INFO] TELEGRAM_BOT_TOKEN not configured — running web-only mode.")


@app.on_event("shutdown")
async def shutdown():
    global telegram_app
    if telegram_app:
        logger.info("Shutting down Telegram Bot application...")
        try:
            await telegram_app.stop()
            await telegram_app.shutdown()
            logger.info("Telegram Bot shut down cleanly.")
        except Exception as e:
            logger.error(f"Error during Telegram bot shutdown: {e}")


class ChatRequest(BaseModel):
    message: str
    language: str = "en"
    session_id: Optional[str] = None
    history: Optional[List[Dict]] = None


class ChatStreamRequest(BaseModel):
    """Request body for the Server-Sent Events streaming endpoint."""
    message: str
    language: str = "en"
    history: Optional[List[Dict]] = None


class ChatResponseModel(BaseModel):
    answer: str
    language: str
    sources: List[str]
    scheme_names: List[str]
    retrieval_time_ms: float
    llm_time_ms: float
    total_time_ms: float
    confidence: float
    input_translation_ms: float = 0.0
    output_translation_ms: float = 0.0
    session_id: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    engine_loaded: bool
    chunks_in_index: int
    telegram_bot_loaded: bool
    telegram_webhook_registered: bool
    version: str


# ===== API ROUTES =====
@app.get("/api/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="ok",
        engine_loaded=engine is not None,
        chunks_in_index=len(engine.vector_store.chunks) if engine else 0,
        telegram_bot_loaded=telegram_app is not None,
        telegram_webhook_registered=webhook_registered,
        version="1.0.0"
    )


@app.post("/api/chat", response_model=ChatResponseModel)
async def chat(request: ChatRequest):
    if not engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    try:
        result = engine.chat(
            user_message=request.message,
            language=request.language,
            conversation_history=request.history
        )
        return ChatResponseModel(
            answer=result.answer, language=result.language, sources=result.sources,
            scheme_names=result.scheme_names, retrieval_time_ms=result.retrieval_time_ms,
            llm_time_ms=result.llm_time_ms, total_time_ms=result.total_time_ms,
            confidence=result.confidence,
            input_translation_ms=result.input_translation_ms,
            output_translation_ms=result.output_translation_ms,
            session_id=request.session_id
        )
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat/stream")
async def chat_stream(request: ChatStreamRequest):
    """
    Server-Sent Events (SSE) endpoint for word-by-word LLM response streaming.

    Uses engine.chat_stream_async() which is a true async generator backed by
    the Gemini SDK's native async API (client.aio.models.generate_content_stream).
    Each LLM chunk is split into individual words server-side, so the browser
    receives one SSE frame per word — producing genuine word-by-word rendering.

    Each SSE frame carries a JSON object:
      - During generation:  {"token": "<word>",    "done": false}
      - On completion:      {"token": "",           "done": true}
      - On error:           {"error": "<message>",  "done": true}
    """
    if not engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")

    async def event_generator():
        try:
            async for token in engine.chat_stream_async(
                user_message=request.message,
                language=request.language,
                conversation_history=request.history,
            ):
                if token:
                    payload = json.dumps({"token": token, "done": False}, ensure_ascii=False)
                    yield f"data: {payload}\n\n"
            # Signal completion to the client
            yield f"data: {json.dumps({'token': '', 'done': True})}\n\n"
        except Exception as exc:
            logger.error(f"Stream endpoint error: {exc}", exc_info=True)
            error_payload = json.dumps({"error": str(exc), "done": True}, ensure_ascii=False)
            yield f"data: {error_payload}\n\n"

    sse_headers = {
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",   # Prevents Nginx from buffering the SSE stream
        "Connection": "keep-alive",
    }
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers=sse_headers,
    )


# ===== TELEGRAM WEBHOOK ENDPOINTS =====
@app.post("/api/telegram-webhook")
@app.post("/telegram-webhook")
async def telegram_webhook(request: Request):
    """
    Receives incoming Telegram updates via Webhook POST request and dispatches them
    through the python-telegram-bot handler pipeline.
    """
    if not telegram_app:
        raise HTTPException(status_code=503, detail="Telegram bot is not initialized. Set TELEGRAM_BOT_TOKEN.")
    try:
        data = await request.json()
        await process_telegram_update(telegram_app, data)
        return JSONResponse({"status": "ok"})
    except Exception as e:
        logger.error(f"Error processing Telegram webhook update: {e}", exc_info=True)
        # Return 200 to Telegram so it doesn't repeatedly retry malformed updates
        return JSONResponse({"status": "error", "message": str(e)}, status_code=200)


@app.post("/api/upload-policy")
async def upload_policy(file: UploadFile = File(...), scheme_name: Optional[str] = None):
    if not engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    content = await file.read()
    suffix = Path(file.filename).suffix.lower()
    scheme = scheme_name or Path(file.filename).stem.replace('_', ' ').title()
    if suffix == '.pdf':
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        chunks = engine.processor.process_pdf(tmp_path, scheme)
        if chunks:
            engine.vector_store.add_chunks(chunks, engine.embedder)
            engine.vector_store.save()
        Path(tmp_path).unlink(missing_ok=True)
        chunks_added = len(chunks)
    else:
        text = content.decode('utf-8', errors='ignore')
        chunks_added = engine.add_document(text, scheme, file.filename)
    return {"success": True, "chunks_added": chunks_added, "scheme_name": scheme}


@app.get("/api/schemes")
async def list_schemes():
    if not engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    schemes = {}
    for chunk in engine.vector_store.chunks:
        s = chunk.scheme_name
        schemes[s] = schemes.get(s, {"name": s, "chunk_count": 0, "source": chunk.source_file})
        schemes[s]["chunk_count"] += 1
    return {"schemes": list(schemes.values()), "total": len(schemes)}


@app.get("/api/search")
async def semantic_search(q: str, top_k: int = 5):
    if not engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    results = engine.retrieve(q, top_k=top_k)
    return {"query": q, "results": [
        {"scheme": r.chunk.scheme_name, "section": r.chunk.section,
         "content": r.chunk.content[:300] + "...", "score": round(r.score, 3)}
        for r in results
    ]}


@app.get("/api/stats")
async def get_stats():
    if not engine:
        return {"error": "Engine not initialized"}
    chunks = engine.vector_store.chunks
    scheme_counts = {}
    for c in chunks:
        scheme_counts[c.scheme_name] = scheme_counts.get(c.scheme_name, 0) + 1
    return {"total_chunks": len(chunks), "total_schemes": len(scheme_counts), "scheme_distribution": scheme_counts}


# ===== FRONTEND FILE ROUTES (after /api routes) =====
NO_CACHE_HEADERS = {"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache", "Expires": "0"}

@app.get("/style.css")
async def serve_css():
    return FileResponse(str(frontend_path / "style.css"), media_type="text/css", headers=NO_CACHE_HEADERS)


@app.get("/app.js")
async def serve_js():
    return FileResponse(str(frontend_path / "app.js"), media_type="application/javascript", headers=NO_CACHE_HEADERS)


@app.get("/dashboard.html")
async def serve_dashboard():
    return FileResponse(str(frontend_path / "dashboard.html"), media_type="text/html", headers=NO_CACHE_HEADERS)


@app.get("/favicon.ico")
async def favicon():
    return Response(status_code=204)


@app.get("/")
async def root():
    index = frontend_path / "index.html"
    if index.exists():
        return FileResponse(str(index), media_type="text/html", headers=NO_CACHE_HEADERS)
    return JSONResponse({"message": "NyayaBot API", "docs": "/api/docs"})


if __name__ == "__main__":
    uvicorn.run("backend.server:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=False, log_level="info")
