import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

app = FastAPI(
    title="ClaimSure API",
    description="AI-powered Medical Insurance Claim Dispute Resolver with Healthcare Triage Backend",
    version="1.0.0"
)

# CORS Configuration
allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "")
if allowed_origins_env:
    origins = [origin.strip() for origin in allowed_origins_env.split(",") if origin.strip()]
else:
    origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://.*\.vercel\.app|http://localhost:\d+",
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include routers
from routers import triage, documents, coverage, dispute, evaluation

app.include_router(triage.router, prefix="/triage", tags=["Symptom Triage"])
app.include_router(coverage.router, prefix="/coverage", tags=["Pre-Visit Coverage Check"])
app.include_router(dispute.router, prefix="/dispute", tags=["Claim Validator & Dispute Analyzer"])
app.include_router(documents.router, tags=["Dashboard Cases History"])
app.include_router(evaluation.router, prefix="/evaluate", tags=["RAGAS Evaluation"])

@app.get("/")
async def root():
    return {"message": "Welcome to the ClaimSure API. The service is running."}

@app.get("/health")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    # Start command for local development
    uvicorn.run("main:app", host="0.0.0.0", port=10000, reload=True)

print("FastAPI startup complete")
