import os
import sys

# Add backend directory to sys.path to allow imports when running from root directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

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
    # Standard local development origins (wildcard is not allowed when allow_credentials=True)
    origins = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173"
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://.*\.vercel\.app|http://localhost:\d+",
    allow_credentials=True,
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

@app.get("/dns-test")
async def dns_test():
    import socket
    import urllib.request
    import json
    import ssl
    
    domains = [
        "google.com",
        "huggingface.co",
        "api-inference.huggingface.co",
        "router.huggingface.co",
        "github.com",
        "cloudflare.com"
    ]
    results = {}
    
    # Test standard DNS resolution (using original socket.getaddrinfo if patched, or standard socket)
    # Let's inspect socket.getaddrinfo to see if it is custom or original
    is_patched = hasattr(socket, "getaddrinfo") and socket.getaddrinfo.__name__ == "custom_getaddrinfo"
    results["_dns_status"] = {"monkeypatched": is_patched}
    
    for domain in domains:
        try:
            # We call socket.gethostbyname which uses getaddrinfo under the hood
            ip = socket.gethostbyname(domain)
            results[domain] = {"status": "success", "ip": ip}
        except Exception as e:
            results[domain] = {"status": "failed", "error": str(e)}
            
    # Test direct connection to IP addresses (DNS over HTTPS IPs)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    for ip in ["1.1.1.1", "8.8.8.8"]:
        try:
            # Test direct HTTP/HTTPS connection to bypass local DNS entirely
            with urllib.request.urlopen(f"https://{ip}/dns-query?name=google.com&type=A", context=ctx, timeout=3) as resp:
                results[f"_ip_conn_{ip}"] = {"status": "success", "http_code": resp.status}
        except Exception as e:
            results[f"_ip_conn_{ip}"] = {"status": "failed", "error": str(e)}
            
    return results

if __name__ == "__main__":
    import uvicorn
    # Start command for local development
    uvicorn.run("main:app", host="0.0.0.0", port=10000, reload=True)

print("FastAPI startup complete")
