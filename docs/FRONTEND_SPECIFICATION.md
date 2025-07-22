# ToggleBank RAG Frontend Specification

## System Overview
ToggleBank RAG is an anti-hallucination banking assistant with real-time quality monitoring. The backend processes user queries through LaunchDarkly AI Configs, AWS Bedrock, and custom fact-checking.

## API Endpoints

### 1. Chat Endpoint
```
POST /api/chat
Content-Type: application/json
Authorization: Bearer {API_KEY}
```

**Request:**
```json
{
  "message": "What are my Silver tier benefits?",
  "user": {
    "id": "user-12345",
    "name": "Catherine Liu",
    "location": "Boston, MA", 
    "tier": "Silver",
    "userName": "Catherine Liu"
  },
  "session_id": "session-67890"
}
```

**Response:**
```json
{
  "success": true,
  "response": {
    "message": "As a Silver tier member, you enjoy...",
    "model": "us.anthropic.claude-sonnet-4-20250514-v1:0",
    "timestamp": "2024-01-15T10:30:00Z"
  },
  "metrics": {
    "source_fidelity": 0.88,
    "relevance": 1.0,
    "factual_accuracy": 0.75,
    "tokens": {"input": 1250, "output": 340, "total": 1590},
    "latency_ms": 2450
  }
}
```

### 2. Feedback Endpoint
```
POST /api/feedback
```

**Request:**
```json
{
  "session_id": "session-67890",
  "message_id": "msg-12345",
  "feedback": "positive",
  "user": {"id": "user-12345"}
}
```

### 3. Health Check
```
GET /api/health
```

## Required Data Types

```typescript
interface User {
  id: string;
  name: string;
  location: string;
  tier: "Bronze" | "Silver" | "Gold" | "Platinum" | "Diamond";
  userName: string;
}

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  metrics?: {
    source_fidelity: number;
    relevance: number;
    factual_accuracy: number;
    tokens: {input: number, output: number, total: number};
    latency_ms: number;
  };
}
```

## Key Features to Implement

1. **Chat Interface**: Real-time conversation with message history
2. **User Context**: Display user info (name, tier, location) 
3. **Quality Metrics**: Show source fidelity, relevance, and factual accuracy scores
4. **Feedback System**: Thumbs up/down for responses
5. **Loading States**: Handle API latency gracefully
6. **Error Handling**: Display user-friendly error messages
7. **Session Management**: Maintain conversation context

## Metrics Display
- **Source Fidelity**: How closely response follows source (0-1)
- **Relevance**: Topic relevance score (0-1)  
- **Factual Accuracy**: ⭐ Anti-hallucination score (0-1)
  - 0.8-1.0: Excellent (green)
  - 0.6-0.8: Good (yellow)
  - 0.0-0.6: Poor (red)

## Environment Variables
```env
REACT_APP_API_KEY=your-api-key
REACT_APP_API_BASE_URL=http://localhost:8000
```

## Sample User Context
```json
{
  "id": "user-12345",
  "name": "Catherine Liu",
  "location": "Boston, MA",
  "tier": "Silver", 
  "userName": "Catherine Liu"
}
```

## Error Handling
- 400: Invalid request parameters
- 401: Unauthorized (invalid API key)
- 503: Service unavailable (LaunchDarkly/AWS down)
- 429: Rate limited

## Rate Limiting
- 100 requests/minute per user
- Headers: X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset

## React Hook Example

```typescript
import { useState, useCallback } from 'react';

interface UseChatReturn {
  sendMessage: (message: string) => Promise<void>;
  messages: ChatMessage[];
  loading: boolean;
  error: string | null;
}

export function useToggleBankChat(user: User): UseChatReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sendMessage = useCallback(async (message: string) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${process.env.REACT_APP_API_KEY}`
        },
        body: JSON.stringify({
          message,
          user,
          session_id: 'session-' + Date.now()
        })
      });
      
      const data = await response.json();
      
      if (data.success) {
        setMessages(prev => [...prev, 
          { role: 'user', content: message, timestamp: new Date().toISOString() },
          { 
            role: 'assistant', 
            content: data.response.message, 
            timestamp: data.response.timestamp,
            metrics: data.metrics
          }
        ]);
      } else {
        setError(data.error.message);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [user]);

  return { sendMessage, messages, loading, error };
}
```

## UI Components Needed

1. **ChatContainer**: Main chat interface
2. **MessageList**: Display conversation history
3. **MessageInput**: Text input for user messages
4. **UserInfo**: Display user context (name, tier, location)
5. **MetricsDisplay**: Show quality scores with color coding
6. **FeedbackButtons**: Thumbs up/down for responses
7. **LoadingSpinner**: Show during API calls
8. **ErrorMessage**: Display errors gracefully

## Styling Guidelines

- Use a banking-appropriate color scheme (blues, grays, professional)
- Display metrics with color coding (green/yellow/red)
- Make the chat interface responsive
- Include proper loading states and animations
- Ensure accessibility compliance

This specification provides everything needed to build a production-ready frontend for the ToggleBank RAG system with anti-hallucination monitoring.
