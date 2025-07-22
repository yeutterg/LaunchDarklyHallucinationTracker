#!/usr/bin/env python3
"""
Script to generate architecture diagram as an image
Uses the Mermaid Live Editor API to render the diagram
"""

import urllib.request
import base64
import json
import os

def generate_mermaid_image():
    # Mermaid diagram code
    mermaid_code = """
graph TD
    A[User Query] --> B[LaunchDarkly AI Config]
    B --> C[Enhanced RAG Retrieval]
    C --> D[AWS Bedrock LLM]
    D --> E[Bedrock Guardrails]
    E --> F[Custom Factual Accuracy Checker]
    F --> G[Multi-Metric Response]
    G --> H[LaunchDarkly Metrics Dashboard]
    
    %% Data Sources
    I[40 Banking Policies] --> C
    J[68 Customer Profiles] --> C
    K[AWS Knowledge Base] --> D
    
    %% AI Configs
    L[Main AI Config<br/>Strict Anti-Hallucination Prompts] --> B
    M[LLM-as-Judge Config<br/>Fact Verification] --> F
    
    %% Metrics
    E --> N[Source Fidelity Metric]
    E --> O[Relevance Metric]
    F --> P[Factual Accuracy Metric]
    
    N --> G
    O --> G
    P --> G
    
    %% Styling
    classDef userInput fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef aiConfig fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef bedrock fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef custom fill:#e8f5e8,stroke:#1b5e20,stroke-width:2px
    classDef metrics fill:#fce4ec,stroke:#880e4f,stroke-width:2px
    classDef data fill:#f1f8e9,stroke:#33691e,stroke-width:2px
    
    class A userInput
    class B,L,M aiConfig
    class D,E,K bedrock
    class F,C custom
    class G,H,N,O,P metrics
    class I,J data
    """
    
    # Encode the Mermaid code
    encoded_code = base64.b64encode(mermaid_code.encode()).decode()
    
    # Create the URL for the Mermaid Live Editor
    mermaid_url = f"https://mermaid.ink/img/{encoded_code}?type=png&width=1200&height=800"
    
    print("🎨 Generating architecture diagram...")
    print(f"📊 Mermaid Live Editor URL: {mermaid_url}")
    
    # Try to download the image
    try:
        with urllib.request.urlopen(mermaid_url, timeout=30) as response:
            # Save the image
            with open("architecture_diagram.png", "wb") as f:
                f.write(response.read())
            print("✅ Architecture diagram saved as 'architecture_diagram.png'")
    except Exception as e:
        print(f"❌ Error generating image: {e}")
        print("💡 You can manually visit the Mermaid Live Editor URL above to download the image")
    
    # Also create a simple SVG version
    svg_url = f"https://mermaid.ink/svg/{encoded_code}"
    print(f"🎨 SVG version: {svg_url}")
    
    # Create a markdown file with the image
    markdown_content = f"""# ToggleBank Anti-Hallucination Architecture

## Architecture Diagram

![ToggleBank Architecture](architecture_diagram.png)

## Alternative Links

- **PNG Image**: {mermaid_url}
- **SVG Version**: {svg_url}
- **Interactive Editor**: https://mermaid.live/edit#{encoded_code}

## Architecture Flow

1. **User Query** → Enhanced with customer context
2. **LaunchDarkly AI Config** → Applies strict anti-hallucination prompts
3. **Enhanced RAG** → Retrieves 20 chunks + policy documents
4. **AWS Bedrock LLM** → Generates response with Knowledge Base
5. **Bedrock Guardrails** → Monitors source fidelity & relevance
6. **Custom Fact Checker** → LLM-based factual accuracy verification ⭐
7. **Multi-Metric Response** → Combines all three metrics
8. **LaunchDarkly Dashboard** → Real-time monitoring & alerting

## Component Legend

- 🔵 **User Input** (light blue) - Customer queries and context
- 🟣 **AI Configs** (purple) - LaunchDarkly AI configuration management
- 🟠 **AWS Bedrock** (orange) - AWS Bedrock LLM and guardrails
- 🟢 **Custom Components** (green) - Enhanced RAG and fact checking
- 🔴 **Metrics** (pink) - Monitoring and evaluation metrics
- 🟢 **Data Sources** (light green) - Banking policies and customer profiles
"""
    
    with open("architecture_diagram.md", "w") as f:
        f.write(markdown_content)
    
    print("📝 Architecture documentation saved as 'architecture_diagram.md'")

if __name__ == "__main__":
    generate_mermaid_image() 