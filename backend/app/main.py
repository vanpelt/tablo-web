from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import log_buffer as _log_buffer
from .routes import auth, channels, iptv, stream
from .state import state

_log_buffer.install()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await state.restore_session()
    yield
    await state.http.aclose()

app = FastAPI(title="Tablo Web", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Explicitly include routers with the /api prefix
app.include_router(auth.router)
app.include_router(channels.router)
app.include_router(iptv.router)
app.include_router(stream.router, prefix="/api")

@app.get("/api/health")
async def health():
    return {"ok": True}
