import os
import sys

# Add backend directory to sys.path to allow imports when running from root directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import re

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
    # Standard local development origins and direct Vercel URL
    origins = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "https://claim-sure-d11s1xz3l-sowmya-sris-projects-950cb19d.vercel.app"
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://.*\.vercel\.app|http://localhost:\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback
    print("Unhandled exception occurred:", str(exc))
    traceback.print_exc()
    
    origin = request.headers.get("origin")
    headers = {}
    if origin:
        allowed_pattern = r"https://.*\.vercel\.app|http://localhost:\d+|http://127.0.0.1:\d+"
        if re.fullmatch(allowed_pattern, origin) or origin in origins:
            headers["Access-Control-Allow-Origin"] = origin
            headers["Access-Control-Allow-Credentials"] = "true"
            headers["Vary"] = "Origin"
            
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal Server Error: {str(exc)}"},
        headers=headers
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
