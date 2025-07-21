#!/usr/bin/env python3
"""
chat_rag_guardrail.py – Terminal chat bot with:
  • LaunchDarkly AI Configs           – prompt/model governance
  • S3-backed RAG retrieval           – reference source
  • Bedrock inline guardrail          – hallucination & relevance check
  • Live metrics & user feedback      – sent back to LaunchDarkly

Keys come from .env in the same folder.
"""
import os, sys, json, signal, hashlib, logging, textwrap, time, uuid, random
from typing import List, Dict, Any

import dotenv, boto3, botocore
import ldclient
from ldclient.config import Config
from ldclient import Context
from ldai.client import LDAIClient, AIConfig, ModelConfig
from ldai.tracker import FeedbackKind

# ── setup & helpers ───────────────────────────────────────────────────────────
dotenv.load_dotenv()

LD_SDK   = os.getenv("LAUNCHDARKLY_SDK_KEY")
LD_KEY   = os.getenv("LAUNCHDARKLY_AI_CONFIG_KEY")
LD_JUDGE_KEY = os.getenv("LAUNCHDARKLY_LLM_JUDGE_KEY")
REGION   = os.getenv("AWS_REGION", "us-east-1")

# These will now come from LaunchDarkly AI config instead of env vars
# GR_ID    = os.getenv("AWS_GUARDRAIL_ID")
# GR_VER   = os.getenv("AWS_GUARDRAIL_VERSION", "DRAFT")
# KB_ID    = os.getenv("RAG_BUCKET")  
# PREFIX   = os.getenv("RAG_PREFIX", "rag/passages/")  

if not (LD_SDK and LD_KEY and LD_JUDGE_KEY):
    sys.exit("✖  Missing required env vars – check your .env file")

# LD initialisation
ldclient.set_config(Config(LD_SDK))
ld = ldclient.get()
if not ld.is_initialized():
    sys.exit("✖  LaunchDarkly SDK failed to initialise")

ai_client = LDAIClient(ld)

# AWS clients
bedrock = boto3.client("bedrock-runtime", region_name=REGION)
bedrock_agent = boto3.client("bedrock-agent-runtime", region_name=REGION)

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(message)s")

def print_box(title: str, text: str) -> None:
    lines = textwrap.wrap(text, 78)
    width = max(len(title), *(len(l) for l in lines)) + 4
    print("┌" + "─"*width + "┐")
    print("│ " + title.center(width-2) + " │")
    print("├" + "─"*width + "┤")
    for l in lines:
        print("│ " + l.ljust(width-2) + " │")
    print("└" + "─"*width + "┘")

def get_kb_passages(question: str, kb_id: str) -> str:
    """
    Query AWS Bedrock Knowledge Base using vector search
    """
    try:
        response = bedrock_agent.retrieve(
            knowledgeBaseId=kb_id,
            retrievalQuery={
                'text': question
            },
            retrievalConfiguration={
                'vectorSearchConfiguration': {
                    'numberOfResults': 25  # Expanded window for better accuracy
                }
            }
        )
        
        passages = []
        for result in response.get('retrievalResults', []):
            content = result.get('content', {}).get('text', '')
            if content:
                passages.append(content)
        
        if passages:
            return '\n\n---\n\n'.join(passages)
        else:
            return "No relevant passages found."
            
    except botocore.exceptions.ClientError as e:
        logging.error("Knowledge Base retrieval error: %s", e)
        return "Error retrieving passages from knowledge base."

def map_messages(msgs) -> List[Dict[str, Any]]:
    """Convert messages, filtering out system messages for separate handling"""
    return [{"role": m.role, "content": [{"text": m.content}]} 
            for m in msgs if m.role in ["user", "assistant"]]

def extract_system_messages(msgs) -> List[Dict[str, str]]:
    """Extract system messages for the system parameter"""
    return [{"text": m.content} for m in msgs if m.role == "system"]

def build_guardrail_prompt(passages: str, question: str) -> str:
    return f"Source Information:\n{passages}\n\nCustomer Question: {question}"

# Simple Message class to match expected structure
class SimpleMessage:
    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content
    
    def to_dict(self):
        return {
            "role": self.role,
            "content": self.content
        }

# graceful Ctrl-C
signal.signal(signal.SIGINT, lambda *_: sys.exit("\n👋  bye!"))

def list_ai_configs(ai_client):
    """List all available AI Configs for debugging"""
    try:
        print("🔍 Debug: Attempting to list all AI Configs...")
        # Note: This is a simplified approach - you might need to use the LaunchDarkly API directly
        print("   Note: AI Config listing requires direct API access")
        print("   Please check your LaunchDarkly dashboard for available AI Configs")
    except Exception as e:
        print(f"❌ Error listing AI Configs: {e}")

def check_factual_accuracy(source_passages: str, response_text: str, generator_model_id: str, custom_params: dict, context: Context) -> float:
    """
    Check factual accuracy by extracting and comparing key facts
    Returns a score from 0.0 to 1.0 representing factual accuracy
    
    Uses a dedicated LaunchDarkly AI Config for LLM-as-judge evaluation
    """
    
    # Get eval frequency to control cost
    eval_freq = float(custom_params.get('eval_freq', '1.0'))
    random_value = random.random()
    should_evaluate = random_value < eval_freq
    
    if not should_evaluate:
        return None
    
    # Get LLM-as-judge configuration from separate LaunchDarkly AI config
    judge_default_cfg = AIConfig(
        enabled=True, 
        model=ModelConfig(name="us.anthropic.claude-3-5-sonnet-20241022-v2:0"), 
        messages=[]
    )
    
    # Pass the actual content as variables to LaunchDarkly for template replacement
    # Include user context so judge knows WHO the response is about
    judge_variables = {
        "source_passages": source_passages,
        "response_text": response_text,
        "user_context": context.name or "Anonymous User"  # Get from LaunchDarkly context
    }
    
    judge_cfg, judge_tracker = ai_client.config(LD_JUDGE_KEY, context, judge_default_cfg, judge_variables)
    
    # Get judge model from LaunchDarkly config
    fact_checker_model = judge_cfg.model.name if judge_cfg.model else "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
    
    # Get the prompt from LaunchDarkly AI config (variables already replaced)
    if not (judge_cfg.messages and len(judge_cfg.messages) > 0):
        raise ValueError("LLM-as-judge AI config must have a system message - no fallback available")
    
    fact_check_prompt = judge_cfg.messages[0].content

    
    # Execute fact-checking

    try:
        # Call LLM-as-judge and track with SDK
        fact_check_response = bedrock.converse(
            modelId=fact_checker_model,  # Use LLM-as-judge from LaunchDarkly config
            messages=[
                {
                    "role": "user", 
                    "content": [{"text": fact_check_prompt}]
                }
            ]
        )
        
        # Use provider-specific tracking method for judge model
        judge_tracker.track_bedrock_converse_metrics(fact_check_response)
        
        # Track judge model performance
        
        fact_result = fact_check_response["output"]["message"]["content"][0]["text"]
        
        # Process judge response
        
        # Parse JSON response
        import json
        try:
            fact_data = json.loads(fact_result)
            return fact_data.get("accuracy_score", 0.0)
        except json.JSONDecodeError:
            # Fallback: try to extract score from text
            if "accuracy_score" in fact_result:
                import re
                score_match = re.search(r'"accuracy_score":\s*([0-9.]+)', fact_result)
                if score_match:
                    return float(score_match.group(1))
            return 0.0
            
    except Exception as e:
        # Track error for judge model
        judge_tracker.track_error()
        logging.error(f"Factual accuracy check failed: {e}")
        return 0.0

# ── main loop ────────────────────────────────────────────────────────────────
def main() -> None:
    # Generate unique user for fresh experiment exposure each time
    unique_user_key = f"user-{uuid.uuid4().hex[:8]}"
    
    # Set up Catherine Liu's profile for context variables (from customer_024.txt)
    context = Context.builder(unique_user_key).kind("user").name("Catherine Liu").set(
        "location", "Boston, MA"
    ).set(
        "tier", "Silver"
    ).set(
        "userName", "Catherine Liu"
    ).build()
    
    # Default config - will be overridden by LaunchDarkly AI configs
    default_cfg = AIConfig(
        enabled=True, 
        model=ModelConfig(name="us.anthropic.claude-3-5-sonnet-20241022-v2:0"), 
        messages=[]
    )

    # Debug: Show connection info
    print(f"🔍 Debug: LaunchDarkly SDK Key: {LD_SDK[:10]}...")
    print(f"🔍 Debug: AI Config Key: {LD_KEY}")
    print(f"🔍 Debug: Context: {context}")
    
    # Try to list available AI Configs
    list_ai_configs(ai_client)
    
    # Get initial config to extract static parameters (KB_ID, GR_ID, etc.)
    try:
        initial_cfg, _ = ai_client.config(LD_KEY, context, default_cfg, {})
        print(f"🔍 Debug: Config retrieval successful")
    except Exception as e:
        print(f"❌ Error: Failed to retrieve AI Config: {e}")
        print(f"   Please check:")
        print(f"   1. Your LaunchDarkly SDK key is correct")
        print(f"   2. The AI Config key '{LD_KEY}' exists in LaunchDarkly")
        print(f"   3. The AI Config is properly configured")
        sys.exit(1)
    
    # Debug: Check if config was retrieved successfully
    if initial_cfg is None:
        print(f"❌ Error: Could not retrieve AI Config with key: {LD_KEY}")
        print(f"   Please check:")
        print(f"   1. Your LaunchDarkly SDK key is correct")
        print(f"   2. The AI Config key '{LD_KEY}' exists in LaunchDarkly")
        print(f"   3. The AI Config is properly configured")
        sys.exit(1)
    
    # Get configuration values from LaunchDarkly AI config custom parameters
    config_dict = initial_cfg.to_dict()
    print(f"🔍 Debug: Retrieved config: {config_dict}")
    
    model_config = config_dict.get('model', {})
    if not model_config:
        print(f"❌ Error: No 'model' section found in AI Config")
        print(f"   Config structure: {config_dict}")
        sys.exit(1)
        
    custom_params = model_config.get('custom', {})
    print(f"🔍 Debug: Custom params: {custom_params}")
    

    
    KB_ID = custom_params.get('kb_id')
    GR_ID = custom_params.get('gr_id') 
    GR_VER = custom_params.get('gr_version', 'DRAFT')
    
    # Validate required parameters
    if not KB_ID:
        logging.error(f"kb_id not found. custom_params: {custom_params}")
        sys.exit("✖  Missing kb_id in LaunchDarkly AI config custom parameters")
    if not GR_ID:
        logging.error(f"gr_id not found. custom_params: {custom_params}")
        sys.exit("✖  Missing gr_id in LaunchDarkly AI config custom parameters")
    
    # Get evaluation frequency configuration
    eval_freq = float(custom_params.get('eval_freq', '1.0'))  # Default to 100% evaluation

    # Get model name from the initial config for display
    model_id = initial_cfg.model.name if initial_cfg.model else "us.anthropic.claude-3-5-sonnet-20241022-v2:0"

    print_box("READY", f"User: Catherine Liu (Silver Tier)\nCity: Boston, MA | Average Balance: <1k\nModel: {model_id}\nGuardrail: {GR_ID} (v{GR_VER})\nKnowledge Base: {KB_ID}\nType 'exit' to quit.")

    # Welcome message
    print("\n🤖  Hi, this is Bot from ToggleBank, how can I help you?")

    while True:
        user = input("\n🧑  You: ").strip()
        if user.lower() in {"exit", "quit"}:
            break

        # Get AI config with user input as variable for this specific query
        query_variables = {"userInput": user}
        cfg, tracker = ai_client.config(LD_KEY, context, default_cfg, query_variables)
        
        model_id = cfg.model.name if cfg.model else "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
        history  = list(cfg.messages) if cfg.messages else []   # seed messages from LD (with variables replaced)

        # Extract user context from LaunchDarkly context for personalized search
        user_context_name = context.name  # Get from LaunchDarkly context
        
        # Enhance RAG query with user context for better retrieval
        if any(word in user.lower() for word in ["my", "i", "me", "mine"]):
            # Personal queries should include the user's name for better RAG results
            enhanced_query = f"{user_context_name} {user}"
        else:
            # Non-personal queries don't need user context
            enhanced_query = user
            
        passages = get_kb_passages(enhanced_query, KB_ID)
        
        # Show both original and enhanced query in debug
        query_info = f"Original Query: {user}\nEnhanced Query: {enhanced_query}" if enhanced_query != user else f"Query: {user}"
        print_box("RAG DEBUG", f"Knowledge Base ID: {KB_ID}\n{query_info}\nPassages Retrieved: {passages[:200]}..." if len(passages) > 200 else f"Knowledge Base ID: {KB_ID}\n{query_info}\nPassages Retrieved: {passages}")
        
        prompt   = build_guardrail_prompt(passages, user)
        print_box("PROMPT DEBUG", f"Final prompt sent to Bedrock:\n{prompt[:300]}..." if len(prompt) > 300 else prompt)

        # assemble conversation in Bedrock's expected format with proper guardrail structure
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
                        "text": user,
                        "qualifiers": ["query"]
                    }
                }
            }
        ]
        
        convo_msgs = map_messages(history) + [{"role": "user", "content": user_content}]
        system_msgs = extract_system_messages(history)



        try:
            # Build converse parameters
            converse_params = {
                "modelId": model_id,
                "messages": convo_msgs,
                "guardrailConfig": {                            
                    "guardrailIdentifier": GR_ID,
                    "guardrailVersion": GR_VER,
                    "trace": "enabled", 
                },
            }
            
            # Add system messages if any exist
            if system_msgs:
                converse_params["system"] = system_msgs
                
            # Call Bedrock and track with SDK
            raw = bedrock.converse(**converse_params)
            
            # Extract token usage for display metrics
            usage = raw.get("usage", {})
            input_tokens = usage.get("inputTokens", 0)
            output_tokens = usage.get("outputTokens", 0)
            total_tokens = input_tokens + output_tokens
            
            # Use provider-specific tracking method for Bedrock
            tracker.track_bedrock_converse_metrics(raw)
            
            # Create a wrapped response object for compatibility
            reply_obj = {
                "output": raw["output"],
                "metrics": {
                    "tokens": {
                        "total": total_tokens,
                        "input": input_tokens,
                        "output": output_tokens
                    }
                }
            }
            


            # trace object now lives at response["trace"]["guardrail"]
            g_trace = raw.get("trace", {}).get("guardrail", {})
            
            # Extract guardrail scores
            
            # Extract grounding and relevance scores from output assessments
            grounding = None
            relevance = None
            
            # Look in outputAssessments for contextual grounding scores
            output_assessments = g_trace.get("outputAssessments", {})
            
            if output_assessments:
                # Get the first (and usually only) guardrail assessment
                guardrail_id = list(output_assessments.keys())[0] if output_assessments else ""
                if guardrail_id and output_assessments.get(guardrail_id):
                    assessments = output_assessments[guardrail_id]
                    if isinstance(assessments, list) and len(assessments) > 0:
                        assessment = assessments[0]
                        # Look for contextual grounding scores in the correct structure
                        if "contextualGroundingPolicy" in assessment:
                            cg_policy = assessment["contextualGroundingPolicy"]
                            if "filters" in cg_policy:
                                for filter_item in cg_policy["filters"]:
                                    if filter_item.get("type") == "GROUNDING":
                                        grounding = filter_item.get("score")
                                    elif filter_item.get("type") == "RELEVANCE":  
                                        relevance = filter_item.get("score")
            
            # Extract contextual grounding metrics if available
            input_assessment = g_trace.get("inputAssessment", {})
            guardrail_id = list(input_assessment.keys())[0] if input_assessment else ""
            grounding_units = 0
            if guardrail_id and input_assessment.get(guardrail_id, {}).get("invocationMetrics", {}).get("usage", {}):
                grounding_units = input_assessment[guardrail_id]["invocationMetrics"]["usage"].get("contextualGroundingPolicyUnits", 0)
        except botocore.exceptions.ClientError as e:
            # Track error with LaunchDarkly
            tracker.track_error()
            logging.error("Bedrock error: %s", e)
            continue

        # Extract response text - handle LaunchDarkly response structure
        if "output" in reply_obj:
            reply_txt = reply_obj["output"]["message"]["content"][0]["text"]
        else:
            # Fallback: extract from raw response structure
            reply_txt = raw["output"]["message"]["content"][0]["text"]
            
        latency   = "N/A"  # Handled by SDK tracking
        
        # Get token usage from our tracked metrics
        input_tokens = reply_obj.get("metrics", {}).get("tokens", {}).get("input", "?")
        output_tokens = reply_obj.get("metrics", {}).get("tokens", {}).get("output", "?")
        
        print_box("ASSISTANT", reply_txt)

        # ── factual accuracy check ────────────────────────────────────────────
        factual_accuracy = check_factual_accuracy(passages, reply_txt, model_id, custom_params, context)
        if factual_accuracy is not None:
            logging.info(f"Accuracy score: {factual_accuracy:.3f}")

        # ── feedback ──────────────────────────────────────────────────────────
        print_box("FEEDBACK", "👍  Was this helpful? (y/n)")
        fb = input("Your answer: ").strip().lower()
        if fb.startswith("y") and tracker:
            tracker.track_feedback({"kind": FeedbackKind.Positive})
        elif fb.startswith("n") and tracker:
            tracker.track_feedback({"kind": FeedbackKind.Negative})

        # ── accuracy metric for LaunchDarkly experiment ──────────────────────
        if grounding is not None:
            # Convert grounding score to percentage and send to LaunchDarkly as Source Fidelity
            grounding_percentage = grounding * 100
            ld.track(
                "$ld:ai:source-fidelity",
                context, 
                data=None,
                metric_value=grounding_percentage
            )
            logging.info(f"Sent source fidelity metric to LaunchDarkly: {grounding_percentage:.1f}%")
            
        # ── relevance metric for LaunchDarkly experiment ───────────────────────
        if relevance is not None:
            # Convert relevance score to percentage and send to LaunchDarkly
            relevance_percentage = relevance * 100
            ld.track(
                "$ld:ai:relevance",
                context, 
                data=None,
                metric_value=relevance_percentage
            )
            logging.info(f"Sent relevance metric to LaunchDarkly: {relevance_percentage:.1f}%")

        # ── accuracy metric for LaunchDarkly (factual accuracy = anti-hallucination) ───────────────────
        if factual_accuracy is not None:
            factual_accuracy_percentage = factual_accuracy * 100
            ld.track(
                "$ld:ai:hallucinations",
                context,
                data=None,
                metric_value=factual_accuracy_percentage
            )
            logging.info(f"Sent accuracy metric to LaunchDarkly: {factual_accuracy_percentage:.1f}%")


        # ── session summary ──────────────────────────────────────────────────
        met = reply_obj.get("metrics", {})
        grounding_str = f"{grounding:.2f}" if grounding is not None else "None"
        relevance_str = f"{relevance:.2f}" if relevance is not None else "None"
        accuracy_str = f"{factual_accuracy:.2f}" if factual_accuracy is not None else "SKIPPED"
        summary = (
            f"Latency: {latency} ms | Bedrock tokens in/out: "
            f"{input_tokens}/{output_tokens} | "
            f"Source Fidelity: {grounding_str} | Relevance: {relevance_str} | "
            f"Accuracy: {accuracy_str}"
        )
        print_box("METRICS", summary)

        # update local history for context
        history.append(SimpleMessage(role="user", content=user))
        history.append(SimpleMessage(role="assistant", content=reply_txt))

        ld.flush()  # push events quickly

    ld.close()
    print("✓  Finished. Goodbye!")

if __name__ == "__main__":
    main()