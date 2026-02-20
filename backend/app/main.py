import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from .core.config import get_settings
from sqlalchemy import text
from .database import init_db, engine
from .api import auth, practices, payers, claims, calls, webhooks, metrics, scheduled_calls, rag, audit, reports

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    if settings.SENTRY_DSN:
        try:
            import sentry_sdk
            sentry_sdk.init(dsn=settings.SENTRY_DSN, environment=settings.APP_ENV, traces_sample_rate=0.1)
        except Exception:
            pass
    init_db()
    yield
    # Shutdown


app = FastAPI(
    title=settings.APP_NAME,
    description="Automate medical billing insurance calls with AI",
    version="0.1.0",
    lifespan=lifespan,
)

# Request ID middleware (Phase 7)
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(practices.router, prefix="/api")
app.include_router(payers.router, prefix="/api")
app.include_router(claims.router, prefix="/api")
app.include_router(calls.router, prefix="/api")
app.include_router(webhooks.router, prefix="/api")
app.include_router(metrics.router, prefix="/api")
app.include_router(scheduled_calls.router, prefix="/api")
app.include_router(rag.router, prefix="/api")
app.include_router(audit.router, prefix="/api")
app.include_router(reports.router, prefix="/api")


@app.get("/")
def root():
    return {"app": settings.APP_NAME, "status": "ok", "env": settings.APP_ENV}


@app.get("/health")
def health():
    """Basic liveness."""
    return {"status": "healthy", "env": settings.APP_ENV}


@app.get("/health/ready")
def health_ready():
    """Readiness: DB and Redis connectivity (Phase 7)."""
    db_ok = True
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        db_ok = False
    redis_ok = True
    try:
        import redis
        r = redis.from_url(settings.REDIS_URL)
        r.ping()
    except Exception:
        redis_ok = False
    ready = db_ok and redis_ok
    return {
        "status": "ready" if ready else "degraded",
        "database": "ok" if db_ok else "error",
        "redis": "ok" if redis_ok else "error",
    }
