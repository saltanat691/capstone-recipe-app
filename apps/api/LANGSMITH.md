# LangSmith Configuration Guide

This guide explains how to configure LangSmith for LLM observability in the Recipe AI System.

## Overview

LangSmith is a platform for debugging, testing, and monitoring LLM applications. It provides:
- **Trace visualization** for LLM calls
- **Prompt tracking** and version management
- **Token usage** and cost monitoring
- **Error debugging** for agent executions
- **Performance metrics** for chains and tools

## Architecture

```
┌─────────────────────────────────────────────────────┐
│            FastAPI Application                       │
│                                                      │
│  ┌────────────────────────────────────────────────┐ │
│  │         LangGraph Agents                       │ │
│  │  (Recipe recommendations, meal planning, etc.) │ │
│  └──────────────────┬─────────────────────────────┘ │
│                     │                                │
│           ┌─────────▼─────────┐                     │
│           │   LangChain Core  │                     │
│           │  (Instrumented)   │                     │
│           └─────────┬─────────┘                     │
└─────────────────────┼─────────────────────────────────┘
                      │
                      │ Automatic Tracing
                      │
               ┌──────▼──────┐
               │  LangSmith  │
               │   (Cloud)   │
               └─────────────┘
```

When configured, LangSmith automatically captures:
- LLM prompts and completions
- Agent reasoning steps
- Tool calls and results
- Token counts and latencies
- Error stack traces

## Configuration

### Environment Variables

LangSmith is configured via environment variables in `apps/api/.env`:

```env
# Enable LangSmith tracing
LANGSMITH_TRACING=true

# LangSmith API key (get from https://smith.langchain.com)
LANGSMITH_API_KEY=your_api_key_here

# Project name (organizes traces in LangSmith)
LANGSMITH_PROJECT=recipe-ai-system-dev

# LangSmith endpoint (default, usually doesn't need to change)
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
```

### LLM Provider Keys

Configure the LLM providers you'll use:

```env
# OpenAI (for GPT models)
OPENAI_API_KEY=sk-...

# Anthropic (for Claude models)
ANTHROPIC_API_KEY=sk-ant-...
```

## Getting Started

### 1. Sign Up for LangSmith

1. Go to https://smith.langchain.com
2. Sign up for a free account
3. Create a new project (e.g., "recipe-ai-system-dev")
4. Get your API key from Settings → API Keys

### 2. Configure Environment

Update `apps/api/.env`:

```env
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=lsv2_pt_xxxxxxxxxxxxxxxxxxxxx
LANGSMITH_PROJECT=recipe-ai-system-dev

# Add at least one LLM provider
OPENAI_API_KEY=sk-...
```

### 3. Verify Configuration

When you start the API, you should see:

```
✓ LangSmith tracing configured
  project: recipe-ai-system-dev
  endpoint: https://api.smith.langchain.com
```

And:

```
LLM configuration status
  openai_configured: true
  anthropic_configured: false
  langsmith_enabled: true
```

### 4. Test Tracing (Future)

Once LangGraph agents are implemented:

```python
from langchain_openai import ChatOpenAI

# This call will be automatically traced to LangSmith
llm = ChatOpenAI(model="gpt-4")
response = llm.invoke("Suggest a recipe with chicken")
```

Check https://smith.langchain.com to see the trace!

## Features

### Automatic Instrumentation

No code changes needed! When LangSmith is configured, it automatically captures:

**LLM Calls:**
```python
# Automatically traced
llm = ChatOpenAI(model="gpt-4")
response = llm.invoke("Your prompt here")
```

**Agent Executions:**
```python
# Automatically traced
from langgraph.graph import StateGraph

graph = StateGraph(...)
result = graph.invoke({"input": "..."})
```

**Chain Invocations:**
```python
# Automatically traced
chain = prompt | llm | output_parser
result = chain.invoke({"query": "..."})
```

### Trace Data Captured

Each trace includes:

1. **Input/Output**
   - Full prompt sent to LLM
   - Complete response received
   - Intermediate steps in chains

2. **Metadata**
   - Model name and parameters
   - Token counts (prompt, completion, total)
   - Latency and timing
   - Cost estimation

3. **Context**
   - Agent state at each step
   - Tool calls and results
   - Error messages and stack traces

4. **Tags**
   - Custom tags for filtering
   - Environment (dev, staging, prod)
   - User IDs or session IDs

## Viewing Traces

### LangSmith Dashboard

1. Go to https://smith.langchain.com
2. Select your project
3. View traces in real-time

### Filtering Traces

Filter by:
- **Status**: Success, Error
- **Model**: gpt-4, claude-3-opus, etc.
- **Latency**: Slow requests (>1s)
- **Cost**: Expensive calls
- **Tags**: Custom filters

### Trace Details

Click on a trace to see:
- Full conversation history
- Token usage breakdown
- Latency per step
- Error details
- Input/output for each step

## Integration with OpenTelemetry

LangSmith and OpenTelemetry work together:

**OpenTelemetry (Tempo):**
- Tracks HTTP requests
- Database queries
- System performance
- Distributed tracing

**LangSmith:**
- LLM-specific observability
- Prompt engineering insights
- Token usage and costs
- Agent reasoning steps

**Correlation:**
Both systems will have separate trace IDs, but you can correlate them using:
- Request timestamps
- User IDs or session IDs
- Custom tags in both systems

## Configuration Options

### Disabling LangSmith

Set in `.env`:
```env
LANGSMITH_TRACING=false
```

The API will log:
```
LangSmith tracing is disabled
```

### Changing Projects

Different projects for different environments:

```env
# Development
LANGSMITH_PROJECT=recipe-ai-system-dev

# Staging
LANGSMITH_PROJECT=recipe-ai-system-staging

# Production
LANGSMITH_PROJECT=recipe-ai-system-prod
```

### Custom Tags

Add custom tags to traces (when implementing agents):

```python
from langsmith import Client

client = Client()
with client.trace(
    name="recipe_recommendation",
    tags=["user:123", "cuisine:italian"],
) as run:
    # Your LLM code here
    pass
```

## Cost Tracking

LangSmith automatically tracks token usage and estimates costs:

**View Costs:**
1. Go to your project in LangSmith
2. Click "Analytics" tab
3. View:
   - Total tokens used
   - Estimated costs
   - Cost per request
   - Trends over time

**Cost Optimization:**
- Identify expensive prompts
- Compare model costs (GPT-4 vs GPT-3.5)
- Find inefficient chains
- Optimize token usage

## Troubleshooting

### No Traces Appearing

1. **Check API key:**
   ```bash
   # Verify key is set
   echo $LANGSMITH_API_KEY
   ```

2. **Check startup logs:**
   ```
   ✓ LangSmith tracing configured
   ```

3. **Verify LLM calls are being made:**
   LangSmith only traces when LLM calls happen

4. **Check LangSmith status:**
   Visit https://status.langchain.com

### API Key Invalid

If you see errors about invalid API key:

1. Regenerate key in LangSmith Settings
2. Update `.env` file
3. Restart the API

### Traces in Wrong Project

Update `LANGSMITH_PROJECT` in `.env` to match your project name in LangSmith.

### High Volume Warning

LangSmith has usage limits on free tier. If you hit limits:

1. Upgrade to paid plan
2. Sample traces (keep 10% of traces)
3. Use separate projects for dev/prod

## Best Practices

### 1. Use Descriptive Project Names

```env
# Good
LANGSMITH_PROJECT=recipe-ai-system-dev

# Bad
LANGSMITH_PROJECT=test
```

### 2. Add Custom Metadata

```python
# Add context to traces
with client.trace(
    name="generate_meal_plan",
    metadata={
        "user_id": user_id,
        "days": 7,
        "cuisine": "italian",
    }
):
    # Agent code
    pass
```

### 3. Tag Traces for Filtering

```python
tags = [
    f"environment:{settings.ENVIRONMENT}",
    f"user:{user_id}",
    f"agent:meal_planner",
]
```

### 4. Monitor Costs Regularly

- Check weekly token usage
- Set up budget alerts
- Optimize expensive prompts

### 5. Use Different Projects per Environment

- `recipe-ai-system-dev` for development
- `recipe-ai-system-staging` for staging
- `recipe-ai-system-prod` for production

## Security

### API Key Security

- **Never commit** API keys to version control
- Use `.env` file (in `.gitignore`)
- Rotate keys regularly
- Use different keys per environment

### Data Privacy

- LangSmith logs full prompts and responses
- Don't include PII in prompts
- Review LangSmith's privacy policy
- Use data retention settings

## Utility Functions

The `llm_config.py` module provides utilities:

```python
from app.core.llm_config import (
    setup_langsmith,
    check_llm_configuration,
    get_llm_api_key,
    get_langsmith_url,
)

# Setup (done automatically on startup)
setup_langsmith()

# Check what's configured
status = check_llm_configuration()
# Returns: {"openai": True, "anthropic": False, "langsmith": True}

# Get API key
openai_key = get_llm_api_key("openai")

# Get LangSmith URL for a trace
url = get_langsmith_url(run_id="abc123")
```

## Future Agent Integration

When implementing LangGraph agents:

```python
from langgraph.graph import StateGraph
from langchain_openai import ChatOpenAI

# This will automatically trace to LangSmith
llm = ChatOpenAI(model="gpt-4", temperature=0.7)

# Build your agent
graph = StateGraph(...)

# Invoke - traces appear in LangSmith automatically!
result = graph.invoke({"input": "Suggest a dinner recipe"})
```

No additional code needed for tracing!

## Additional Resources

- [LangSmith Documentation](https://docs.smith.langchain.com/)
- [LangChain Documentation](https://python.langchain.com/docs/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [LangSmith Pricing](https://www.langchain.com/pricing)
- [LangSmith Status](https://status.langchain.com)

## Summary

LangSmith configuration is **ready** but **dormant** until you:
1. Add your API key
2. Implement LangGraph agents
3. Make LLM calls

Once agents are implemented, all LLM activity will be automatically traced to LangSmith with zero code changes!