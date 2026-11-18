from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.rate_limit import RateLimitMiddleware
from app.routers import auth, admin, session, leaderboard
from app.core.background_tasks import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    start_scheduler()
    print("Python Challenge Platform API ishga tushdi")
    yield
    # Shutdown
    stop_scheduler()
    print("API to'xtatildi")



app = FastAPI(
    title="Python Challenge Platform",
    description="30 Kunlik Python Challenge Platformasi API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware)

# Routerlarni ulash
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(session.router)
app.include_router(leaderboard.router)


@app.get("/")
async def root():
    return {
        "name": "Python Challenge Platform API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
