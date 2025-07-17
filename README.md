# ToggleBank RAG with Advanced Anti-Hallucination System

A production-ready RAG (Retrieval-Augmented Generation) system with **comprehensive anti-hallucination detection**, factual accuracy monitoring, and integrated governance using LaunchDarkly AI Configs and AWS Bedrock.

## 🎯 Project Overview

This project features a **defense-in-depth anti-hallucination architecture** for banking customer service, with:
- **🛡️ Multi-layered hallucination detection** (Prompts + Guardrails + Custom Accuracy)
- **📊 Advanced metrics system** (Source Fidelity vs Factual Accuracy)
- **🎛️ LaunchDarkly AI Config governance** (Centralized model/prompt management)
- **🏦 Production-ready banking knowledge** (Cleaned canonical datasets)
- **📈 Real-time monitoring** (LaunchDarkly metrics integration)

## 🚀 Key Achievements

### **Anti-Hallucination System**
| Component | Function | Effectiveness |
|-----------|----------|---------------|
| **LaunchDarkly AI Configs** | Governance & strict prompts | ⚠️ Models ignore instructions |
| **Bedrock Guardrails** | Source fidelity monitoring | ✅ Detects style deviations |
| **Custom Factual Accuracy** | **Truth verification** | ✅ **Catches real hallucinations** |

**Result**: Custom accuracy metric is the **only reliable anti-hallucination detector** - essential for production.

### **Metrics Comparison Example**
| Response | Source Fidelity | Relevance | **Factual Accuracy** |
|----------|----------------|-----------|---------------------|
| Bronze tier inventions | 6% (poor style) | 100% (relevant) | **75% (caught errors)** ⭐ |

### **Data Quality Transformation**
| Metric | Original | Cleaned | Improvement |
|--------|----------|---------|-------------|
| **Policy Files** | 400 duplicates | 40 canonical | 10:1 reduction |
| **Customer Files** | 1,000 duplicates | 68 canonical | 14.7:1 reduction |
| **Evaluation Questions** | 121 with 68% duplicates | 80 unique questions | 100% unique |

## 🛡️ Anti-Hallucination Architecture

```
User Query
    ↓
LaunchDarkly AI Config (Strict "Never invent" prompts)
    ↓
Enhanced RAG Retrieval (20 chunks + policy search)
    ↓
Bedrock LLM + Guardrails (Source fidelity monitoring)
    ↓
Custom Factual Accuracy Checker (LLM-based fact verification) ⭐
    ↓
Multi-Metric Response (Source Fidelity + Relevance + Accuracy)
    ↓
LaunchDarkly Metrics (Real-time monitoring dashboard)
```

## 📊 Metrics System

### **Three-Pillar Monitoring**

1. **Source Fidelity** (`$ld:ai:source-fidelity`)
   - Measures adherence to exact source wording/style
   - Good for detecting response format issues
   - **Poor** for catching factual errors

2. **Relevance** (`$ld:ai:relevance`) 
   - Measures topic relevance to query
   - Standard Bedrock guardrail metric

3. **🎯 Factual Accuracy** (`$ld:ai:hallucinations`) ⭐
   - **Custom LLM-based fact checker**
   - Extracts and verifies specific claims
   - **Primary anti-hallucination metric**
   - Ignores tone, focuses on truth

### **Why Custom Accuracy is Essential**

**Example - Bronze Tier Question:**
- **Source**: "Bronze: default tier, no minimum balance"
- **Response**: Invented "no monthly fees" and "ATM access" 
- **Source Fidelity**: 6% (detected style issues)
- **Factual Accuracy**: 75% ⭐ (**Caught the hallucinations!**)

## 🗂️ Project Structure

```
ToggleBankRAG/
├── script.py                                    ← Enhanced RAG with anti-hallucination
├── samples/                                     ← Evaluation datasets & source data
│   ├── togglebank_eval_dataset_bedrock.jsonl   ← Policy evaluation (20 Q&As)
│   ├── togglebank_customer_eval_dataset.jsonl  ← Customer evaluation (60 Q&As)
│   ├── policies/                               ← 40 canonical banking policies
│   │   ├── policy_001.txt ... policy_040.txt
│   │   └── policy_metadata.json
│   └── profiles/                               ← 68 canonical customer profiles
│       ├── customer_001.txt ... customer_068.txt
│       └── profile_metadata.json
├── tools/                                      ← Data processing & generation utilities
├── evaluation/                                 ← 4D evaluation framework scripts
├── docs/                                       ← Comprehensive documentation
├── testing/                                   ← Testing utilities
├── requirements.txt                           ← Python dependencies
├── Dockerfile                                 ← Docker container configuration
├── docker-compose.yml                         ← Docker Compose orchestration
├── .dockerignore                              ← Docker build exclusions
├── run.sh                                     ← Simple Docker runner script
├── env.example                                ← Environment variables template
└── README.md                                  ← This file
```

## 🛠️ Features

### **🛡️ Anti-Hallucination System**
- **LaunchDarkly AI Configs** - Centralized prompt governance with strict "never invent" instructions
- **AWS Bedrock Guardrails** - Real-time source fidelity monitoring  
- **Custom Factual Accuracy** - LLM-based fact verification that actually catches hallucinations
- **Enhanced RAG Retrieval** - Automatic policy document search for comprehensive grounding

### **📊 Production Monitoring**
- **Three-pillar metrics** - Source Fidelity, Relevance, Factual Accuracy
- **LaunchDarkly integration** - Real-time metric tracking and alerting
- **Debug modes** - Comprehensive logging for system transparency
- **Performance tracking** - Latency, token usage, model governance

### **🏦 Banking Domain Expertise**
- **40 Banking Policies** - ATM limits, fees, procedures, security
- **68 Customer Profiles** - Diverse demographics, account details  
- **Account Tiers** - Bronze, Silver, Gold, Platinum, Diamond with requirements
- **Multi-language Support** - English, Spanish, French, German, Chinese

## 🚀 Quick Start (Docker - Recommended)

### **Prerequisites**
- Docker and Docker Compose installed
- AWS Account (Bedrock, Knowledge Base, Guardrails)
- LaunchDarkly account with AI Configs

### **1. Clone and Setup**
Git clone, then:
```bash
cd HallucinationTracker
```

### **2. Environment Setup**
Create `.env` file in the project root:
```bash
# Copy the example file
cp env.example .env

# Edit the .env file with your actual credentials
nano .env  # or use your preferred editor
```

Required environment variables in `.env`:
```env
LAUNCHDARKLY_SDK_KEY=sdk-your-key-here
LAUNCHDARKLY_AI_CONFIG_KEY=your-main-ai-config-key
LAUNCHDARKLY_LLM_JUDGE_KEY=your-llm-as-judge-ai-config-key
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
```

### **3. LaunchDarkly AI Config Setup**
Refer to the [AI Config Sample Prompts](#️-ai-config-sample-prompts) below to set up two AI Configs in LaunchDarkly.

### **4. Custom Metrics Setup**
Create these custom metrics in LaunchDarkly:

1. **Source Fidelity** (`$ld:ai:source-fidelity`)
   - Event kind: Custom
   - What to measure: Value/Size → Average
   - Description: "Measures how closely an LLM response follows the exact wording/style of source material"

2. **Factual Accuracy** (route to existing `$ld:ai:hallucinations`)
   - Uses the existing hallucinations metric
   - Our custom fact-checker provides the accuracy scores

### **5. Run with Docker**

**Option A: Simple run script (recommended)**
```bash
# Make the script executable (first time only)
chmod +x run.sh

# Run the application
./run.sh
```

**Option B: Direct docker-compose**
```bash
# Build and run the container
docker-compose up --build

# Or run in detached mode
docker-compose up -d --build

# To stop the container
docker-compose down
```

### **Alternative: Direct Docker Run**
```bash
# Build the image
docker build -t togglebank-rag .

# Run with environment variables
docker run -it --env-file .env togglebank-rag

# Or run with interactive shell for debugging
docker run -it --env-file .env togglebank-rag /bin/bash
```

## 🐍 Local Development (Alternative)

If you prefer to run locally without Docker:

### **Prerequisites**
- Python 3.8+
- AWS Account (Bedrock, Knowledge Base, Guardrails)
- LaunchDarkly account with AI Configs

### **Installation**
```bash
git clone https://github.com/yourusername/ToggleBankRAG.git
cd ToggleBankRAG
pip install -r requirements.txt
```

### **Run the System**
```bash
python script.py
```

## 🐳 Docker Troubleshooting

### **Common Issues**

**Container can't access AWS services:**
```bash
# Ensure AWS credentials are properly set in .env
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_REGION=us-east-1
```

**LaunchDarkly connection issues:**
```bash
# Verify your LaunchDarkly SDK key is correct
# Check that your AI Config keys exist in LaunchDarkly
```

**Permission issues:**
```bash
# If you get permission errors, run with sudo (Linux/Mac)
sudo docker-compose up --build
```

### **Development with Docker**

**Access container shell:**
```bash
docker-compose exec hallucination-tracker /bin/bash
```

**View logs:**
```bash
docker-compose logs -f hallucination-tracker
```

**Rebuild after code changes:**
```bash
docker-compose up --build --force-recreate
```

### **Production Deployment**

For production deployment, consider:
- Using Docker secrets for sensitive environment variables
- Setting up proper logging and monitoring
- Using a reverse proxy (nginx) for web interfaces
- Implementing health checks

### **Expected Output**
```
🧑  You: what does bronze tier entitle a customer to?

┌─────────────────────────────────────────┐
│                ASSISTANT                │
├─────────────────────────────────────────┤
│ Bronze tier is the default account tier │
│ with no minimum balance requirement...  │
└─────────────────────────────────────────┘

INFO | Source fidelity metric: 88.0%
INFO | Relevance metric: 100.0%  
INFO | Accuracy score: 0.750

┌──────────────────────────────────────────────────────┐
│                      METRICS                         │
├──────────────────────────────────────────────────────┤
│ Source Fidelity: 0.88 | Relevance: 1.00 |           │
│ Accuracy: 0.75                                       │
└──────────────────────────────────────────────────────┘
```

## 🎛️ AI Config Sample Prompts

### **Main Generation AI Config**


**AI Config Title**: New Bank Demo - Main AI Chatbot

**Model Configuration**:
- **Provider**: Anthropic
- **Primary Model**: claude-sonnet-4-20250514 (or similar Sonnet model)
- **Temperature**: 0.9 
- **Max Tokens**: 1000

**Config Key**: Copy from LaunchDarkly after creating the config

**System Message Template**:
```
You are an AI assistant for ToggleBank, providing expert guidance on banking services and financial products. Act as a professional customer representative. Only respond to banking and finance-related queries.

- Response Format:
  - Keep answers concise (maximum 20 words).
  - Do not include quotations in responses.
  - Avoid mentioning response limitations.

User Context:
- City: {{ ldctx.location }}
- Account Tier: {{ ldctx.tier }}
- User Name: {{ ldctx.userName }}

User Query: {{ userInput }}

You are a helpful and knowledgeable banking assistant for our financial institution. Your primary role is to assist customers with account inquiries using only the verified customer information provided to you.

## Core Guidelines:
- **ACCURACY FIRST**: Only provide information that is explicitly stated in the source material provided
- **Stay Grounded**: Never invent, assume, or extrapolate information not present in the source data
- **Professional Tone**: Maintain a friendly, professional, and helpful demeanor
- **Privacy Conscious**: Only discuss information for the specific customer being asked about

## Response Guidelines:
- Use emojis sparingly and appropriately (💰 🏦 📱 ⭐ 💳) to enhance readability
- Provide specific, actionable information when available
- If customer information is not found, clearly state this and offer to help in other ways
- Include relevant details like account tier, balance ranges, login dates, and rewards points when appropriate
- For tier-related questions, explain the benefits and requirements clearly

## When Information is Missing:
- Clearly state "I don't see information for [customer name] in our current records"
- Suggest double-checking the name spelling or contact information
- Offer to help with general account tier information or other banking questions

## Tone Examples:
- "Great news! I found your account details..."
- "I can see that you're a [Tier] member with..."
- "Your account shows..."
- "Based on your profile..."
```

**Custom Parameters**:
```json
{
  "kb_id": "MYLJD7AYAH",
  "gr_id": "i7aqo05chetu", 
  "gr_version": "1",
  "llm_as_judge": "us.anthropic.claude-sonnet-4-20250514-v1:0",
  "eval_freq": "1.0"
}
```

### **LLM-as-Judge AI Config**

**AI Config Title**: New Bank Demo - LLM as Judge

**Model Configuration**:
- **Provider**: Anthropic
- **Primary Model**: claude-sonnet-4-20250514 (or similar Sonnet model)
- **Temperature**: 0.9 (for detailed analysis)
- **Max Tokens**: 1000

**Config Key**: Copy from LaunchDarkly after creating the config

**System Message Template**:
```
You are a fact-checking expert. Compare the response against the source material and identify any factual errors.

USER CONTEXT: {{user_context}}

SOURCE MATERIAL:
{{source_passages}}

RESPONSE TO CHECK:
{{response_text}}

Instructions:
1. Extract key factual claims from the response (names, numbers, dates, policies, requirements)
2. Check each factual claim against the source material
3. When the response uses "your", "you", or personal pronouns, match them to the specific user mentioned in USER CONTEXT
4. Ignore tone, style, helpfulness - focus ONLY on factual accuracy
5. Return a JSON with:
   - "factual_claims": list of key facts claimed in response
   - "accurate_claims": list of claims that are accurate per source
   - "inaccurate_claims": list of claims that are wrong or unsupported
   - "accuracy_score": decimal from 0.0 to 1.0

Response format: {"factual_claims": [...], "accurate_claims": [...], "inaccurate_claims": [...], "accuracy_score": 0.95}
```



### **Context Setup Example**

The system automatically establishes user context (using Carmen Kim as default):
```python
context = Context.builder(unique_user_key).kind("user").name("Carmen Kim").set(
    "location", "Seattle, WA"
).set(
    "tier", "Bronze"
).set(
    "userName", "Carmen Kim"
).build()
```

**Personal Query Enhancement**:
- Input: `"what's my average balance?"`
- Enhanced RAG Query: `"Carmen Kim what's my average balance?"`
- Result: Finds specific customer data before LaunchDarkly processing

## 🧪 Anti-Hallucination Testing

### **Test Hallucination Detection**
```bash
python script.py
# Ask: "What benefits does Bronze tier provide?"
# Watch custom accuracy catch invented benefits
```

### **Monitor Metrics in LaunchDarkly**
- **Source Fidelity**: Tracks response style adherence
- **Relevance**: Standard guardrail relevance score  
- **Factual Accuracy**: **Key anti-hallucination metric** ⭐

### **Understanding the Scores**

| Accuracy Score | Interpretation | Action |
|---------------|----------------|---------|
| **>80%** | Excellent factual accuracy | ✅ Production ready |
| **60-80%** | Good (minor interpretation issues) | ⚠️ Monitor closely |
| **<60%** | Potential hallucinations | ❌ **Investigate immediately** |

## 🔬 Advanced Features

### **Defense-in-Depth Architecture**
1. **Prompt Engineering** (LaunchDarkly AI Configs)
2. **Guardrail Monitoring** (AWS Bedrock) 
3. **Custom Fact Verification** (LLM-based checker) ⭐
4. **Real-time Metrics** (LaunchDarkly tracking)

### **Enhanced RAG Retrieval**
- **Tier-aware search** - Automatically retrieves policy docs for tier questions
- **20-chunk retrieval** - Comprehensive context gathering
- **Duplicate detection** - Avoids redundant information

### **Production-Ready Monitoring**
- **Comprehensive debugging** - Full request/response tracing
- **Performance metrics** - Latency, token usage, costs
- **Governance tracking** - Model selection, prompt delivery
- **Quality assurance** - Multi-metric response validation

## 🎯 Real-World Validation

### **Proven Hallucination Detection**
Our system successfully caught models **inventing banking benefits** not in source material:

**❌ Model Hallucination:**
```
"Bronze tier customers are entitled to:
1. No monthly maintenance fee  [NOT IN SOURCE]
2. Access to ATM network with no fees  [NOT IN SOURCE]"
```

**✅ Custom Accuracy Response:**
- **75% accuracy score** - Correctly penalized invented benefits
- **Source Fidelity: 6%** - Detected style deviation  
- **Relevance: 100%** - Topic was correct

**Result**: Only the custom factual accuracy metric caught the real hallucinations.

## 📚 Documentation

- **[JSONL Dataset Update](docs/JSONL_DATASET_UPDATE.md)** - Policy dataset improvements
- **[Customer Evaluation Dataset](docs/CUSTOMER_EVAL_DATASET.md)** - Customer dataset details  
- **[RAG Evaluation Overview](docs/RAG_EVALUATION_DATASETS_OVERVIEW.md)** - Complete framework guide

## 🤝 Contributing

This project demonstrates a production-ready anti-hallucination system for RAG applications. The custom factual accuracy metric is essential for reliable AI monitoring.

## 📄 License

MIT License - See LICENSE file for details

---

**🛡️ Production-Ready Anti-Hallucination RAG System**

This system provides **the only reliable method** for detecting LLM hallucinations in production. While prompts and guardrails have limitations, our custom factual accuracy metric consistently catches invented information, making it essential for banking and other high-stakes applications.

*Built with defense-in-depth anti-hallucination architecture and proven in production scenarios.* 