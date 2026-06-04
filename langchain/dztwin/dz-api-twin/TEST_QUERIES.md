# Test Queries for RAG Testing

This file contains pre-written test queries organized by category for efficient manual testing.

---

## 🎯 Category 1: Authentication & Authorization

### Basic Authentication Queries
```
1. "How do I authenticate with the API?"
2. "What authentication methods are supported?"
3. "Where do I put my API key?"
4. "How do I get an access token?"
5. "What's the difference between API keys and OAuth?"
```

### Expected Behavior
- Should retrieve authentication documentation
- Should mention API keys, tokens, or OAuth
- Should include code examples if available
- Sources should point to auth-related pages

---

## 🎯 Category 2: CRUD Operations

### Create Operations
```
1. "How do I create a new customer?"
2. "What's the process for adding a user?"
3. "How can I create a new record?"
4. "Show me how to add a new item"
```

### Read Operations
```
1. "How do I retrieve customer information?"
2. "How can I fetch user data?"
3. "Show me how to get a list of items"
4. "How do I search for records?"
```

### Update Operations
```
1. "How do I update customer details?"
2. "What's the process for modifying a record?"
3. "How can I change user information?"
```

### Delete Operations
```
1. "How do I delete a customer?"
2. "What's the process for removing a record?"
3. "How can I cancel or delete an item?"
```

### Expected Behavior
- Should retrieve endpoint-specific documentation
- Should include HTTP methods (POST, GET, PUT, DELETE)
- Should show request/response examples
- Should mention required fields

---

## 🎯 Category 3: Error Handling

### Error Queries
```
1. "What happens if an API call fails?"
2. "How do I handle errors?"
3. "What are the common error codes?"
4. "What does error 404 mean?"
5. "How do I debug API errors?"
6. "What should I do if I get a 401 error?"
```

### Expected Behavior
- Should retrieve error handling documentation
- Should list error codes and meanings
- Should provide troubleshooting steps
- Should mention retry strategies

---

## 🎯 Category 4: Rate Limiting & Quotas

### Rate Limit Queries
```
1. "What are the rate limits?"
2. "How many requests can I make per minute?"
3. "What happens if I exceed the rate limit?"
4. "How do I check my API usage?"
5. "Are there different rate limits for different endpoints?"
```

### Expected Behavior
- Should retrieve rate limiting documentation
- Should mention specific limits (requests/second, etc.)
- Should explain rate limit headers
- Should describe throttling behavior

---

## 🎯 Category 5: Webhooks & Events

### Webhook Queries
```
1. "How do webhooks work?"
2. "How do I set up webhook notifications?"
3. "What events can trigger webhooks?"
4. "How do I verify webhook signatures?"
5. "What's the webhook payload format?"
```

### Expected Behavior
- Should retrieve webhook documentation
- Should list available events
- Should show payload examples
- Should mention security/verification

---

## 🎯 Category 6: Pagination & Filtering

### Pagination Queries
```
1. "How do I paginate through results?"
2. "What's the maximum page size?"
3. "How do I get the next page of results?"
4. "How does cursor-based pagination work?"
```

### Filtering Queries
```
1. "How do I filter results?"
2. "What query parameters are supported?"
3. "How can I search by date range?"
4. "How do I sort results?"
```

### Expected Behavior
- Should retrieve pagination/filtering docs
- Should show query parameter examples
- Should mention limits and defaults
- Should explain cursor vs offset pagination

---

## 🎯 Category 7: Data Formats & Schemas

### Format Queries
```
1. "What data format does the API use?"
2. "Show me the request schema"
3. "What fields are required?"
4. "What's the response format?"
5. "How do I send JSON data?"
```

### Expected Behavior
- Should retrieve schema documentation
- Should show JSON examples
- Should list required vs optional fields
- Should mention data types

---

## 🎯 Category 8: Semantic Search Tests

### Synonym Tests (Same Meaning, Different Words)
```
1. "How do I authenticate?" vs "How do I log in?" vs "How do I verify my identity?"
2. "Create a customer" vs "Add a user" vs "Register a new account"
3. "Delete a record" vs "Remove an item" vs "Cancel an entry"
4. "Get data" vs "Retrieve information" vs "Fetch details"
```

### Expected Behavior
- All similar queries should retrieve same/similar documents
- Semantic understanding, not just keyword matching
- Relevance scores should be similar (within 0.1)

---

## 🎯 Category 9: Multi-Turn Conversations

### Conversation Flow 1: Customer Creation
```
Turn 1: "How do I create a customer?"
Turn 2: "What fields are required?"
Turn 3: "Can you show me an example?"
Turn 4: "What if the email is invalid?"
```

### Conversation Flow 2: Payment Processing
```
Turn 1: "How do I process a payment?"
Turn 2: "What payment methods are supported?"
Turn 3: "How do I handle failed payments?"
Turn 4: "Can I refund a payment?"
```

### Conversation Flow 3: Troubleshooting
```
Turn 1: "I'm getting a 401 error"
Turn 2: "I'm using an API key"
Turn 3: "Where should I put the API key?"
Turn 4: "It's still not working"
```

### Expected Behavior
- AI maintains context across turns
- Doesn't repeat information unnecessarily
- Provides progressively detailed information
- References previous turns naturally

---

## 🎯 Category 10: Edge Cases & Stress Tests

### Ambiguous Queries
```
1. "How does it work?" (vague)
2. "Tell me about the API" (too broad)
3. "What can I do?" (open-ended)
4. "Help" (single word)
```

### Off-Topic Queries
```
1. "What's the weather today?"
2. "Tell me a joke"
3. "Who won the Super Bowl?"
4. "What's 2+2?"
```

### Complex Queries
```
1. "How do I create a customer, add a payment method, and process a charge all in one transaction?"
2. "What's the difference between synchronous and asynchronous webhooks, and which should I use for real-time notifications?"
3. "Explain the complete authentication flow from initial API key generation to making authenticated requests with proper error handling"
```

### Expected Behavior
- Ambiguous: AI asks for clarification or provides general overview
- Off-topic: AI politely redirects to API documentation topics
- Complex: AI breaks down into steps, retrieves multiple relevant docs

---

## 🎯 Category 11: Code Example Requests

### Code Queries
```
1. "Show me a code example for authentication"
2. "Give me a Python example for creating a customer"
3. "How do I do this in JavaScript?"
4. "Show me a cURL command"
5. "What does the request look like?"
```

### Expected Behavior
- Should retrieve code examples from docs
- Should format code with syntax highlighting
- Should include language-specific examples if available
- Should show complete, runnable examples

---

## 🎯 Category 12: Performance & Best Practices

### Best Practice Queries
```
1. "What are the best practices for using the API?"
2. "How do I optimize API performance?"
3. "Should I cache responses?"
4. "How do I handle retries?"
5. "What's the recommended way to batch requests?"
```

### Expected Behavior
- Should retrieve best practices documentation
- Should provide optimization tips
- Should mention caching strategies
- Should explain retry logic

---

## 📊 Test Query Tracking Sheet

Use this to track which queries you've tested:

| Query | Category | Tested | Pass/Fail | Notes |
|-------|----------|--------|-----------|-------|
| "How do I authenticate?" | Auth | [ ] | | |
| "Create a customer" | CRUD | [ ] | | |
| "What are rate limits?" | Rate Limiting | [ ] | | |
| "How do webhooks work?" | Webhooks | [ ] | | |
| "Show me code example" | Code | [ ] | | |

---

## 🎯 Quick Test Script

Copy and paste these queries in sequence for rapid testing:

```
1. How do I authenticate with the API?
2. What are the rate limits?
3. How do I create a customer?
4. What happens if an API call fails?
5. How do webhooks work?
6. Show me a code example
7. What fields are required?
8. How do I handle errors?
9. What's the difference between API keys and OAuth?
10. How do I paginate through results?
```

---

## 🔍 RAG Quality Indicators

For each query, check:

- [ ] **Relevance**: Response directly answers the question
- [ ] **Accuracy**: Information matches documentation
- [ ] **Completeness**: Covers key points from docs
- [ ] **Sources**: 2-5 relevant sources cited
- [ ] **Score**: Top document score > 0.7
- [ ] **Coherence**: Response is well-structured
- [ ] **No Hallucination**: All facts are from docs

---

## 💡 Tips for Effective Testing

1. **Test in Order**: Start with simple queries, progress to complex
2. **Check Logs**: Always verify backend logs show RAG retrieval
3. **Compare Sources**: Click source links to verify accuracy
4. **Test Variations**: Try different phrasings of same question
5. **Note Patterns**: Document which types of queries work best
6. **Test Edge Cases**: Don't just test happy paths
7. **Multi-Turn**: Test conversation context maintenance
8. **Performance**: Note response times for each query

---

## 📝 Query Result Template

For detailed testing, use this template:

```markdown
### Query: "How do I authenticate with the API?"

**Category**: Authentication
**Date**: 2026-02-02
**Time**: 14:30

**RAG Retrieval**:
- Documents Retrieved: 5
- Top Score: 0.87
- Search Time: 1.2s

**Response Quality**:
- Relevance: ✓ High
- Accuracy: ✓ Verified against docs
- Completeness: ✓ Covers key points
- Code Examples: ✓ Included

**Sources Cited**:
1. Authentication Guide - https://docs.example.com/auth
2. API Keys - https://docs.example.com/api-keys
3. OAuth Flow - https://docs.example.com/oauth

**Issues Found**: None

**Notes**: Response was accurate and well-structured. Sources were relevant.
```
