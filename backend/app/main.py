from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.core.database import init_db

app = FastAPI(
    title="Policy Compliance Checker",
    description="Schema-agnostic policy evaluation engine",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
@app.on_event("startup")
async def startup_event():
    init_db()

# Include routes
app.include_router(router, prefix="/api")

@app.get("/")
async def root():
    return {
        "message": "Policy Compliance Checker API",
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}
