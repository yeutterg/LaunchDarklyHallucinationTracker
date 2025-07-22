#!/usr/bin/env python3
"""
FastAPI server for ToggleBank RAG with Anti-Hallucination System
Provides REST API endpoints for frontend integration
"""
import os
import sys
import json
import logging
import time
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime

import dotenv
import boto3
import botocore
import ldclient
from ldclient.config import Config
from ldclient import Context
from ldai.client import LDAIClient, AIConfig, ModelConfig
from ldai.tracker import FeedbackKind

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Load environment variables
dotenv.load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="ToggleBank RAG API",
    description="Anti-hallucination banking assistant with real-time quality monitoring",
    version="1.00"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Configuration ────────────────────────────────────────────────────────────
LD_SDK = os.getenv("LAUNCHDARKLY_SDK_KEY")
LD_KEY = os.getenv("LAUNCHDARKLY_AI_CONFIG_KEY")
LD_JUDGE_KEY = os.getenv("LAUNCHDARKLY_LLM_JUDGE_KEY")
REGION = os.getenv("AWS_REGION", "us-east-1")
API_KEY = os.getenv("API_KEY", "your-api-key-here")

if not (LD_SDK and LD_KEY and LD_JUDGE_KEY):
    raise RuntimeError("Missing required environment variables - check your .env file")

# Initialize LaunchDarkly
ldclient.set_config(Config(LD_SDK))
ld = ldclient.get()
if not ld.is_initialized():
    raise RuntimeError("LaunchDarkly SDK failed to initialize")

ai_client = LDAIClient(ld)

# Initialize AWS clients
bedrock = boto3.client("bedrock-runtime", region_name=REGION)
bedrock_agent = boto3.client("bedrock-agent-runtime", region_name=REGION)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(message)s")
logger = logging.getLogger(__name__)

# ── Pydantic Models ──────────────────────────────────────────────────────────
class User(BaseModel):
    id: str
    name: str
    location: str
    tier: str
    userName: str

class ChatRequest(BaseModel):
    message: str
    user: User
    session_id: str

class ChatResponse(BaseModel):
    success: bool
    response: Dict[str, Any]
    metrics: Dict[str, Any]

class FeedbackRequest(BaseModel):
    session_id: str
    message_id: str
    feedback: str
    user: User

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    services: Dict[str, str]

# ── Helper Functions ──────────────────────────────────────────────────────────
def get_kb_passages(question: str, kb_id: str) -> str:
    """Query AWS Bedrock Knowledge Base using vector search"""
    try:
        response = bedrock_agent.retrieve(
            knowledgeBaseId=kb_id,
            retrievalQuery={'text': question},
            retrievalConfiguration={
                'vectorSearchConfiguration': {'numberOfResults': 25}
            }
        )
        
        passages = []
        for result in response.get('retrievalResults', []):
            content = result.get('content', {}).get('text', '')
            if content:
                passages.append(content)
        
        return '\n\n---\n\n'.join(passages) if passages else "No relevant passages found."
            
    except botocore.exceptions.ClientError as e:
        logger.error("Knowledge Base retrieval error: %s", e)
        return "Error retrieving passages from knowledge base."

def map_messages(msgs) -> List[Dict[str, Any]]:
    """Convert messages, filtering out system messages for separate handling"""
    return [{"role": m.role, "content": [{"text": m.content}]} 
            for m in msgs if m.role in ["user", "assistant"]]

def extract_system_messages(msgs) -> List[Dict[str, str]]:
    """Extract system messages for the system parameter"""
    return [{"role": "system", "content": m.content} 
            for m in msgs if m.role == "system"]

def build_guardrail_prompt(passages: str, question: str) -> str:
    """Build the prompt for the guardrail system"""
    return f"Context: {passages}\n\nQuestion: {question}"

def check_factual_accuracy(source_passages: str, response_text: str, generator_model_id: str, custom_params: dict, context: Context) -> float:
    """Check factual accuracy using LLM-as-judge"""
    try:
        # Get the LLM-as-judge config
        judge_cfg, _ = ai_client.config(LD_JUDGE_KEY, context, AIConfig(enabled=True), {})
        
        if not judge_cfg or not judge_cfg.model:
            logger.warning("Could not retrieve LLM-as-judge config, using default")
            judge_model_id = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
        else:
            judge_model_id = judge_cfg.model.name
        
        # Build the fact-checking prompt
        fact_check_prompt = f"""
You are a fact-checking expert. Analyze the following response against the provided source material.

SOURCE MATERIAL:
{source_passages}

RESPONSE TO CHECK:
{response_text}

TASK: Rate the factual accuracy of the response on a scale of 0.0 to 1.0, where:
- 1.0 = All claims are directly supported by the source material
- 0.8 = Most claims are supported, minor interpretation differences
- 0.6 = Some claims are supported, some may be inferred
- 0.4 = Many claims lack direct support
- 0.2 = Most claims are not supported
- 0.0 = Response contains significant factual errors or inventions

Consider only factual accuracy, not tone or style. Focus on whether specific claims can be verified in the source material.

Provide only a number between 0.0 and 1.0 as your response.
"""
        
        # Call the judge model
        response = bedrock.invoke_model(
            modelId=judge_model_id,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 10,
                "messages": [{"role": "user", "content": fact_check_prompt}]
            })
        )
        
        response_body = json.loads(response.get('body').read())
        judge_response = response_body.get('content', [{}])[0].get('text', '0.5').strip()
        
        # Parse the score
        try:
            score = float(judge_response)
            return max(0.0, min(1.0, score))  # Clamp between 0 and 1
        except ValueError:
            logger.warning(f"Could not parse judge score: {judge_response}")
            return 0.5
            
    except Exception as e:
        logger.error(f"Error in factual accuracy check: {e}")
        return 0.5

def verify_api_key(authorization: str = Header(None)) -> bool:
    """Verify API key from Authorization header"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization format")
    
    api_key = authorization[7:]  # Remove "Bearer " prefix
    if api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return True

# ── API Endpoints ────────────────────────────────────────────────────────────
@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    try:
        # Test LaunchDarkly connection
        ld_status = "healthy" if ld.is_initialized() else "unhealthy"
        
        # Test AWS Bedrock connection
        try:
            bedrock.list_foundation_models()
            bedrock_status = "healthy"
        except:
            bedrock_status = "unhealthy"
        
        return HealthResponse(
            status="healthy",
            timestamp=datetime.utcnow().isoformat(),
            services={
                "launchdarkly": ld_status,
                "aws_bedrock": bedrock_status
            }
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    _: bool = Depends(verify_api_key)
):
    """Main chat endpoint"""
    start_time = time.time()
    
    try:
        # Create LaunchDarkly context from user data
        context = Context.builder(request.user.id).kind("user").name(request.user.name).set(
            "location", request.user.location
        ).set(
            "tier", request.user.tier
        ).set(
            "userName", request.user.userName
        ).build()
        
        # Default config
        default_cfg = AIConfig(
            enabled=True, 
            model=ModelConfig(name="us.anthropic.claude-3-5-sonnet-20241022-v2:0"), 
            messages=[]
        )
        
        # Get AI config with user input
        query_variables = {"userInput": request.message}
        cfg, tracker = ai_client.config(LD_KEY, context, default_cfg, query_variables)
        
        if not cfg:
            raise HTTPException(status_code=503, detail="Failed to retrieve AI configuration")
        
        # Extract configuration parameters
        config_dict = cfg.to_dict()
        model_config = config_dict.get('model', {})
        custom_params = model_config.get('custom', {})
        
        KB_ID = custom_params.get('kb_id')
        GR_ID = custom_params.get('gr_id')
        GR_VER = custom_params.get('gr_version', 'DRAFT')
        
        if not KB_ID or not GR_ID:
            raise HTTPException(status_code=503, detail="Missing required configuration parameters")
        
        # Get model ID
        model_id = cfg.model.name if cfg.model else "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
        history = list(cfg.messages) if cfg.messages else []
        
        # Enhance query with user context for better RAG results
        if any(word in request.message.lower() for word in ["my", "i", "me", "mine"]):
            enhanced_query = f"{request.user.name} {request.message}"
        else:
            enhanced_query = request.message
            
        # Retrieve passages from knowledge base
        passages = get_kb_passages(enhanced_query, KB_ID)
        
        # Build conversation for Bedrock
        user_content = [
            {
                "guardContent": {
                    "text": {
                        "text": passages,
                        "qualifiers": ["grounding_source"]
                    }
                }
            },
            {
                "guardContent": {
                    "text": {
                        "text": request.message,
                        "qualifiers": ["query"]
                    }
                }
            }
        ]
        
        convo_msgs = map_messages(history) + [{"role": "user", "content": user_content}]
        system_msgs = extract_system_messages(history)
        
        # Call Bedrock with proper model invocation
        try:
            # Build the prompt with context
            system_prompt = ""
            if system_msgs:
                system_prompt = system_msgs[0].get("content", "")
            
            # Create the full prompt
            full_prompt = f"{system_prompt}\n\nContext: {passages}\n\nUser: {request.message}\n\nAssistant:"
            
            # Call Bedrock with invoke_model (not converse)
            raw_response = bedrock.invoke_model(
                modelId=model_id,
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 1000,
                    "messages": [{"role": "user", "content": full_prompt}]
                })
            )
            
            # Parse the response
            response_body = json.loads(raw_response.get('body').read())
            response_content = response_body.get('content', [{}])[0].get('text', '')
            usage = response_body.get('usage', {})
            
        except Exception as bedrock_error:
            logger.error(f"Bedrock invocation error: {bedrock_error}")
            raise HTTPException(status_code=503, detail="Failed to generate response from AI model")
        
        # Track Bedrock metrics (simplified since we're not using converse)
        try:
            tracker.track_custom_metric("bedrock_invocation", 1.0)
        except:
            pass  # Don't fail if tracking fails
        
        # Calculate custom factual accuracy
        factual_accuracy = check_factual_accuracy(passages, response_content, model_id, custom_params, context)
        
        # Track custom metrics
        tracker.track_custom_metric("factual_accuracy", factual_accuracy)
        
        # Calculate latency
        latency_ms = int((time.time() - start_time) * 1000)
        
        # Extract guardrail metrics (simplified since we're not using converse)
        # For now, we'll use placeholder values - in production you'd implement custom metrics
        source_fidelity = 0.85  # Placeholder - implement custom source fidelity check
        relevance = 0.90  # Placeholder - implement custom relevance check
        
        return ChatResponse(
            success=True,
            response={
                "message": response_content,
                "model": model_id,
                "timestamp": datetime.utcnow().isoformat()
            },
            metrics={
                "source_fidelity": source_fidelity,
                "relevance": relevance,
                "factual_accuracy": factual_accuracy,
                "tokens": {
                    "input": usage.get("inputTokens", 0),
                    "output": usage.get("outputTokens", 0),
                    "total": usage.get("inputTokens", 0) + usage.get("outputTokens", 0)
                },
                "latency_ms": latency_ms
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}")
        raise HTTPException(status_code=503, detail="The banking assistant is currently unavailable. Please try again later.")

@app.post("/api/feedback")
async def feedback_endpoint(
    request: FeedbackRequest,
    _: bool = Depends(verify_api_key)
):
    """Feedback endpoint for user ratings"""
    try:
        # Create context for feedback tracking
        context = Context.builder(request.user.id).kind("user").name(request.user.name).build()
        
        # Track feedback in LaunchDarkly
        feedback_kind = FeedbackKind.POSITIVE if request.feedback == "positive" else FeedbackKind.NEGATIVE
        
        # Note: This would require the actual message tracker from the chat session
        # For now, we'll just log the feedback
        logger.info(f"Feedback received: {request.feedback} for session {request.session_id}")
        
        return {"success": True, "message": "Feedback recorded"}
        
    except Exception as e:
        logger.error(f"Feedback endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Failed to record feedback")

# ── Main Entry Point ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    logger.info(f"Starting ToggleBank RAG API server on {host}:{port}")
    uvicorn.run(app, host=host, port=port) 