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
REACT_APP_API_KEY=your-api-key-here
REACT_APP_API_BASE_URL=http://localhost:8000
```

**Important:** The API key must match the `API_KEY` value in your backend `.env` file.

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

## Frontend Implementation Guide

### 1. Environment Setup

Create a `.env` file in your frontend project root:

```env
REACT_APP_API_KEY=your-api-key-here
REACT_APP_API_BASE_URL=http://localhost:8000
```

**Important:** The `REACT_APP_API_KEY` must match the `API_KEY` in your backend `.env` file.

### 2. API Client Implementation

```typescript
// api/client.ts
class ToggleBankAPI {
  private baseURL: string;
  private apiKey: string;

  constructor() {
    this.baseURL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';
    this.apiKey = process.env.REACT_APP_API_KEY || '';
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;
    const headers = {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${this.apiKey}`,
      ...options.headers,
    };

    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
    }

    return response.json();
  }

  async sendMessage(message: string, user: User, sessionId: string): Promise<ChatResponse> {
    return this.request<ChatResponse>('/api/chat', {
      method: 'POST',
      body: JSON.stringify({
        message,
        user,
        session_id: sessionId,
      }),
    });
  }

  async sendFeedback(sessionId: string, messageId: string, feedback: string, user: User): Promise<any> {
    return this.request('/api/feedback', {
      method: 'POST',
      body: JSON.stringify({
        session_id: sessionId,
        message_id: messageId,
        feedback,
        user,
      }),
    });
  }

  async checkHealth(): Promise<HealthResponse> {
    return this.request<HealthResponse>('/api/health');
  }
}

export const api = new ToggleBankAPI();
```

### 3. Enhanced React Hook with Error Handling

```typescript
// hooks/useToggleBankChat.ts
import { useState, useCallback, useEffect } from 'react';
import { api } from '../api/client';

interface UseChatReturn {
  sendMessage: (message: string) => Promise<void>;
  messages: ChatMessage[];
  loading: boolean;
  error: string | null;
  isConnected: boolean;
  clearError: () => void;
}

export function useToggleBankChat(user: User): UseChatReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);

  // Check API health on mount
  useEffect(() => {
    const checkHealth = async () => {
      try {
        await api.checkHealth();
        setIsConnected(true);
      } catch (err) {
        setIsConnected(false);
        setError('Unable to connect to banking assistant. Please check if the server is running.');
      }
    };
    checkHealth();
  }, []);

  const sendMessage = useCallback(async (message: string) => {
    if (!isConnected) {
      setError('Not connected to banking assistant. Please refresh the page.');
      return;
    }

    setLoading(true);
    setError(null);
    
    try {
      const sessionId = 'session-' + Date.now();
      const data = await api.sendMessage(message, user, sessionId);
      
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
        setError(data.error?.message || 'Unknown error occurred');
      }
    } catch (err) {
      console.error('Chat API error:', err);
      const errorMessage = err instanceof Error ? err.message : 'Failed to send message';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  }, [user, isConnected]);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return { sendMessage, messages, loading, error, isConnected, clearError };
}
```

### 4. Error Handling Patterns

```typescript
// components/ChatInterface.tsx
import React from 'react';
import { useToggleBankChat } from '../hooks/useToggleBankChat';

export function ChatInterface({ user }: { user: User }) {
  const { sendMessage, messages, loading, error, isConnected, clearError } = useToggleBankChat(user);

  const handleSendMessage = async (message: string) => {
    await sendMessage(message);
  };

  return (
    <div className="chat-interface">
      {/* Connection Status */}
      {!isConnected && (
        <div className="connection-warning">
          ⚠️ Not connected to banking assistant. Please check if the server is running.
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div className="error-message">
          <span>❌ {error}</span>
          <button onClick={clearError}>✕</button>
        </div>
      )}

      {/* Messages */}
      <div className="messages">
        {messages.map((msg, index) => (
          <div key={index} className={`message ${msg.role}`}>
            <div className="content">{msg.content}</div>
            {msg.metrics && (
              <div className="metrics">
                <span className={`metric fidelity ${getMetricColor(msg.metrics.source_fidelity)}`}>
                  Source Fidelity: {Math.round(msg.metrics.source_fidelity * 100)}%
                </span>
                <span className={`metric relevance ${getMetricColor(msg.metrics.relevance)}`}>
                  Relevance: {Math.round(msg.metrics.relevance * 100)}%
                </span>
                <span className={`metric accuracy ${getMetricColor(msg.metrics.factual_accuracy)}`}>
                  Factual Accuracy: {Math.round(msg.metrics.factual_accuracy * 100)}%
                </span>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Input */}
      <div className="input-area">
        <input 
          type="text" 
          placeholder="Ask about your banking services..."
          disabled={loading || !isConnected}
          onKeyPress={(e) => {
            if (e.key === 'Enter' && e.currentTarget.value.trim()) {
              handleSendMessage(e.currentTarget.value.trim());
              e.currentTarget.value = '';
            }
          }}
        />
        {loading && <div className="loading">⏳ Processing...</div>}
      </div>
    </div>
  );
}

function getMetricColor(value: number): string {
  if (value >= 0.8) return 'excellent';
  if (value >= 0.6) return 'good';
  return 'poor';
}
```

### 5. CORS Configuration

If you encounter CORS issues, the backend is already configured to allow all origins. For production, update the CORS configuration in `api_server.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://yourdomain.com"],  # Production domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
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

## Troubleshooting Common Frontend Issues

### 1. "The banking assistant is currently unavailable"

**Causes:**
- Backend API server is not running
- Incorrect API key
- Network connectivity issues
- CORS configuration problems

**Solutions:**
```bash
# Check if backend is running
curl http://localhost:8000/api/health

# Verify API key matches
echo $REACT_APP_API_KEY  # Should match backend API_KEY

# Check backend logs
docker-compose logs hallucination-tracker
```

### 2. CORS Errors

**Symptoms:** Browser console shows CORS policy errors

**Solutions:**
- Backend is already configured to allow all origins
- For production, update CORS origins in `api_server.py`
- Ensure frontend is making requests to the correct URL

### 3. Authentication Errors (401)

**Causes:**
- Missing or incorrect API key
- Wrong Authorization header format

**Solutions:**
```typescript
// Ensure correct header format
headers: {
  'Authorization': `Bearer ${process.env.REACT_APP_API_KEY}`
}
```

### 4. Connection Refused

**Causes:**
- Backend server not running on port 8000
- Docker container not started

**Solutions:**
```bash
# Start the backend
cd HallucinationTracker
./start_api.sh

# Or check if container is running
docker ps | grep togglebank-rag
```

### 5. Environment Variables Not Loading

**Causes:**
- Missing `.env` file
- Incorrect variable names (must start with `REACT_APP_`)
- React app needs restart after env changes

**Solutions:**
```bash
# Create .env file
cp env.example .env

# Restart React development server
npm start
```

## Development Workflow

### 1. Start Backend First
```bash
cd HallucinationTracker
./start_api.sh
```

### 2. Start Frontend
```bash
cd your-frontend-project
npm start
```

### 3. Test Connection
```bash
# Test API health
curl http://localhost:8000/api/health

# Test with API key
curl -H "Authorization: Bearer your-api-key" \
     -H "Content-Type: application/json" \
     -d '{"message":"test","user":{"id":"test","name":"Test","location":"Test","tier":"Silver","userName":"Test"},"session_id":"test"}' \
     http://localhost:8000/api/chat
```

This specification provides everything needed to build a production-ready frontend for the ToggleBank RAG system with anti-hallucination monitoring.
