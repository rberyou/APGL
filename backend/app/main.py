from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routers import auth, jobs, lessons, materials, mistakes, projects, quiz, reviews


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}


app.include_router(auth.router, prefix="/api")
app.include_router(projects.router, prefix="/api")
app.include_router(materials.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")
app.include_router(lessons.router, prefix="/api")
app.include_router(quiz.router, prefix="/api")
app.include_router(reviews.router, prefix="/api")
app.include_router(mistakes.router, prefix="/api")
