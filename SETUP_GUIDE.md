# Setup Guide - AI Voice Form Filling Agent

This guide will walk you through setting up the AI Voice Form Filling Agent step by step.

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Installation Steps](#installation-steps)
3. [Configuration](#configuration)
4. [Running the Server](#running-the-server)
5. [Testing Your Setup](#testing-your-setup)
6. [Troubleshooting](#troubleshooting)

## System Requirements

### Required
- **Python**: 3.10 or higher
- **Operating System**: Linux, macOS, or Windows
- **Memory**: At least 2GB RAM
- **Storage**: 500MB free space

### API Keys (at least one required)
- OpenAI API key (recommended)
- OR Anthropic API key
- OR Google AI API key

## Installation Steps

### Step 1: Install Python

Check if Python 3.10+ is installed:
```bash
python --version
# or
python3 --version
```

If not installed, download from [python.org](https://www.python.org/downloads/).

### Step 2: Clone or Download the Repository

```bash
# If using git
git clone <repository-url>
cd TalkToFillAIAgent

# Or download and extract the ZIP file
```

### Step 3: Create a Virtual Environment

**On Linux/macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**On Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

You should see `(venv)` in your terminal prompt.

### Step 4: Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

This will install all required packages including:
- FastAPI and Uvicorn (web server)
- LangGraph and LangChain (AI framework)
- OpenAI, Anthropic, Google AI clients
- Speech processing libraries
- And more...

**Note:** Installation may take 5-10 minutes depending on your internet speed.

### Step 5: Set Up Environment Variables

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Open `.env` in your text editor:
```bash
# On Linux/macOS
nano .env
# or
vim .env

# On Windows
notepad .env
```

3. Configure at least one LLM provider (see [Configuration](#configuration) section below).

## Configuration

### Option 1: Using OpenAI (Recommended for Beginners)

1. Get an API key from [platform.openai.com](https://platform.openai.com/api-keys)

2. Add to `.env`:
```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-actual-api-key-here
OPENAI_MODEL=gpt-4o-mini
OPENAI_TEMPERATURE=0.7

STT_PROVIDER=openai
TTS_PROVIDER=openai
TTS_VOICE=alloy
```

**Cost Estimate**:
- GPT-4o-mini: ~$0.15 per 1M input tokens, ~$0.60 per 1M output tokens
- Whisper STT: $0.006 per minute
- TTS: $15 per 1M characters

### Option 2: Using Anthropic Claude

1. Get an API key from [console.anthropic.com](https://console.anthropic.com/)

2. Add to `.env`:
```env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-your-actual-api-key-here
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
ANTHROPIC_TEMPERATURE=0.7

# For speech, you'll still need OpenAI or other provider
STT_PROVIDER=openai
TTS_PROVIDER=openai
OPENAI_API_KEY=sk-your-openai-key-here
```

**Cost Estimate**:
- Claude 3.5 Sonnet: ~$3 per 1M input tokens, ~$15 per 1M output tokens

### Option 3: Using Google Gemini

1. Get an API key from [makersuite.google.com](https://makersuite.google.com/app/apikey)

2. Add to `.env`:
```env
LLM_PROVIDER=google
GOOGLE_API_KEY=your-actual-api-key-here
GOOGLE_MODEL=gemini-2.0-flash-exp
GOOGLE_TEMPERATURE=0.7

# For speech
STT_PROVIDER=openai
TTS_PROVIDER=gtts  # Free option using gTTS
OPENAI_API_KEY=sk-your-openai-key-here
```

**Cost Estimate**:
- Gemini 2.0 Flash: Free tier available, then ~$0.075 per 1M input tokens

### Optional: Free TTS with gTTS

If you want to avoid TTS costs, use gTTS (Google Text-to-Speech, free but basic):
```env
TTS_PROVIDER=gtts
```

**Note**: gTTS has limitations:
- Basic voice quality
- Limited voice options
- Requires internet connection

## Running the Server

### Method 1: Direct Python Execution

```bash
python -m src.api
```

### Method 2: Using Uvicorn Directly

```bash
uvicorn src.api:app --host 0.0.0.0 --port 8000 --reload
```

The `--reload` flag enables auto-reload on code changes (useful for development).

### Expected Output

You should see:
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Starting AI Voice Form Filling Agent API
INFO:     LLM Provider: openai
INFO:     STT Provider: openai
INFO:     TTS Provider: openai
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### Accessing the API

- **API Root**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **API Documentation**: http://localhost:8000/redoc

## Testing Your Setup

### Test 1: Health Check

In a new terminal:
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"status": "healthy", "timestamp": "now"}
```

### Test 2: Run Example Client

```bash
# Make sure the server is still running in another terminal
python examples/test_client.py
```

This will:
1. Test railway booking form
2. Test job application form
3. Test multi-field extraction

### Test 3: Manual API Test

Using Python:
```python
import requests
import json

# Load form schema
with open("examples/railway_booking_form.json") as f:
    form_schema = json.load(f)

# Create session
response = requests.post(
    "http://localhost:8000/sessions",
    json={"form_schema": form_schema}
)
print(response.json())
```

## Troubleshooting

### Issue: "ModuleNotFoundError"

**Solution**: Make sure your virtual environment is activated and dependencies are installed:
```bash
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### Issue: "OpenAI API key not configured"

**Solution**:
1. Check that `.env` file exists in the project root
2. Verify `OPENAI_API_KEY` is set correctly (no extra spaces, quotes, etc.)
3. Make sure the key starts with `sk-`

### Issue: "Address already in use"

**Solution**: Another process is using port 8000. Either:
1. Stop the other process
2. Use a different port:
```bash
python -m src.api --port 8001
```

Or in `.env`:
```env
API_PORT=8001
```

### Issue: Server starts but API calls fail

**Possible Causes**:
1. **Invalid API key**: Check your LLM provider API key
2. **Rate limits**: Wait a few minutes if you've hit rate limits
3. **Network issues**: Check your internet connection

**Debug Steps**:
```bash
# Check server logs in the terminal where server is running
# Look for error messages

# Test API availability
curl http://localhost:8000/

# Check specific endpoint
curl http://localhost:8000/health -v
```

### Issue: "Failed to transcribe audio"

**Possible Causes**:
1. Audio file format not supported
2. Audio file too large
3. STT provider API issues

**Solution**:
- Supported formats: WAV, MP3, M4A, FLAC
- Max file size: 25MB (for OpenAI Whisper)
- Check STT provider API status

### Issue: gTTS not working

**Error**: "gtts.tts.gTTSError: Failed to connect"

**Solution**:
- Check internet connection
- Try a different TTS provider:
```env
TTS_PROVIDER=openai
```

### Issue: High memory usage

**Solution**:
- If using local Whisper: Consider using OpenAI API instead
- Clear old sessions periodically
- Use Redis for session management (reduces memory)

### Issue: Slow response times

**Possible Causes**:
1. LLM model is slow
2. Network latency
3. Large conversation history

**Solutions**:
- Use faster models:
  - OpenAI: `gpt-4o-mini` instead of `gpt-4o`
  - Anthropic: `claude-3-haiku` instead of `claude-3-opus`
  - Google: `gemini-2.0-flash-exp` instead of `gemini-1.5-pro`
- Reduce `MAX_CONVERSATION_HISTORY` in `.env`:
```env
MAX_CONVERSATION_HISTORY=10
```

## Advanced Configuration

### Using Redis for Production

1. Install Redis:
```bash
# Docker
docker run -d -p 6379:6379 redis:alpine

# Or install locally
# macOS
brew install redis
redis-server

# Ubuntu
sudo apt-get install redis-server
sudo systemctl start redis
```

2. Update `.env`:
```env
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

3. Install Redis Python client (should already be in requirements.txt):
```bash
pip install redis
```

### Running in Production

For production deployment:

1. Use a production ASGI server:
```bash
pip install gunicorn
gunicorn src.api:app -w 4 -k uvicorn.workers.UvicornWorker
```

2. Set up environment variables:
```env
API_DEBUG=false
LOG_LEVEL=WARNING
```

3. Use HTTPS with a reverse proxy (nginx, Caddy, etc.)

4. Set up monitoring and logging

5. Configure firewall and security

### Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `openai` | LLM provider: openai, anthropic, google |
| `OPENAI_API_KEY` | - | OpenAI API key |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI model name |
| `OPENAI_TEMPERATURE` | `0.7` | Temperature (0.0-1.0) |
| `ANTHROPIC_API_KEY` | - | Anthropic API key |
| `ANTHROPIC_MODEL` | `claude-3-5-sonnet-20241022` | Claude model |
| `GOOGLE_API_KEY` | - | Google AI API key |
| `GOOGLE_MODEL` | `gemini-2.0-flash-exp` | Gemini model |
| `STT_PROVIDER` | `openai` | Speech-to-text provider |
| `STT_LANGUAGE` | `en-US` | Default language for STT |
| `TTS_PROVIDER` | `openai` | Text-to-speech provider |
| `TTS_VOICE` | `alloy` | Voice for TTS |
| `API_HOST` | `0.0.0.0` | API server host |
| `API_PORT` | `8000` | API server port |
| `API_DEBUG` | `true` | Enable debug mode |
| `REDIS_HOST` | `localhost` | Redis host |
| `REDIS_PORT` | `6379` | Redis port |
| `MAX_CONVERSATION_HISTORY` | `20` | Max messages in history |
| `SESSION_TIMEOUT_MINUTES` | `30` | Session expiration time |

## Next Steps

1. **Explore Examples**: Check `examples/` directory for form schemas and test scripts
2. **Read API Documentation**: Visit http://localhost:8000/docs
3. **Create Custom Forms**: Design your own form schemas
4. **Integrate with Your App**: Use the REST API in your application
5. **Deploy to Production**: Follow production deployment guidelines

## Getting Help

- **Documentation**: Check README.md and inline code comments
- **API Docs**: http://localhost:8000/docs
- **Examples**: `examples/` directory
- **Issues**: Open an issue on GitHub

## Summary Checklist

- [ ] Python 3.10+ installed
- [ ] Virtual environment created and activated
- [ ] Dependencies installed via pip
- [ ] `.env` file configured with API keys
- [ ] Server starts successfully
- [ ] Health check passes
- [ ] Example tests run successfully
- [ ] API documentation accessible

If all items are checked, you're ready to use the AI Voice Form Filling Agent! 🎉
