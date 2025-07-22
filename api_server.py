from fastapi import FastAPI, Request, HTTPException, Header, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Literal, Dict, Any
from starlette.responses import JSONResponse
import os

API_KEY = os.getenv("API_KEY", "your-api-key-here")

app = FastAPI()

# Allow all origins for local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Models ---
class User(BaseModel):
    id: str
    name: str
    location: str
    tier: Literal["Bronze", "Silver", "Gold", "Platinum", "Diamond"]
    userName: str

class ChatRequest(BaseModel):
    message: str
    user: User
    session_id: str

class Tokens(BaseModel):
    input: int
    output: int
    total: int

class Metrics(BaseModel):
    source_fidelity: float
    relevance: float
    factual_accuracy: float
    tokens: Tokens
    latency_ms: int

class ChatResponseData(BaseModel):
    message: str
    model: str
    timestamp: str

class ChatResponse(BaseModel):
    success: bool
    response: Optional[ChatResponseData]
    metrics: Optional[Metrics]
    error: Optional[Dict[str, Any]] = None

class FeedbackRequest(BaseModel):
    session_id: str
    message_id: str
    feedback: str
    user: User

# --- Auth Dependency ---
def verify_api_key(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = authorization.split(" ", 1)[1]
    if token != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

# --- Endpoints ---
@app.get("/api/health")
def health():
    return {"status": "ok"}

@app.post("/api/chat", response_model=ChatResponse)
def chat(
    req: ChatRequest,
    _: None = Depends(verify_api_key)
):
    # Mock response
    import datetime
    now = datetime.datetime.utcnow().isoformat() + "Z"
    response = ChatResponse(
        success=True,
        response=ChatResponseData(
            message="As a {} tier member, you enjoy...".format(req.user.tier),
            model="us.anthropic.claude-sonnet-4-20250514-v1:0",
            timestamp=now
        ),
        metrics=Metrics(
            source_fidelity=0.88,
            relevance=1.0,
            factual_accuracy=0.75,
            tokens=Tokens(input=1250, output=340, total=1590),
            latency_ms=2450
        )
    )
    return response

@app.post("/api/feedback")
def feedback(
    req: FeedbackRequest,
    _: None = Depends(verify_api_key)
):
    # Mock: just return success
    return {"success": True, "message": "Feedback received"} 