# AI Voice Agent for Accessible Form Filling

A comprehensive, production-ready AI voice agent system built with **Python**, **LangGraph**, and **multiple LLM providers** that enables users to complete complex forms through natural language voice or text interaction.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green.svg)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2-purple.svg)](https://github.com/langchain-ai/langgraph)

## 🌟 Key Features

### Multi-Model LLM Support
- **OpenAI GPT** (GPT-4o, GPT-4o-mini, GPT-3.5-turbo)
- **Anthropic Claude** (Claude 3.5 Sonnet, Claude 3 Opus/Haiku)
- **Google Gemini** (Gemini 2.0 Flash, Gemini 1.5 Pro)
- Easy switching between providers via configuration

### Intelligent Conversational AI
- **LangGraph-based agentic workflow** for complex multi-turn conversations
- Natural language understanding and field extraction
- Context-aware conversation management
- Proactive clarification questions
- Multi-field extraction from single utterances

### Comprehensive Speech Processing
- **Speech-to-Text**: OpenAI Whisper, Google Cloud Speech, Local Whisper
- **Text-to-Speech**: OpenAI TTS, Google Cloud TTS, gTTS
- Real-time audio transcription and synthesis
- Multi-language support

### Advanced Form Handling
- **Generic form schema** - works with ANY form
- Real-time validation with detailed error messages
- Conditional field logic and dependencies
- Multi-step form support
- Field type support: text, email, date, number, select, multiselect, etc.

### Production-Ready Features
- RESTful API with FastAPI
- Session management (in-memory and Redis)
- Comprehensive error handling
- CORS support for web integration
- Detailed logging and monitoring
- Type-safe with Pydantic models

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Client Application                    │
│         (Web Browser, Mobile App, etc.)                 │
└────────────────────┬────────────────────────────────────┘
                     │ HTTP/REST API
┌────────────────────▼────────────────────────────────────┐
│                   FastAPI Server                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │  API Endpoints                                   │   │
│  │  • Session Management                            │   │
│  │  • Voice/Text Processing                         │   │
│  │  • Form State Retrieval                          │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────┬──────────────────────┬────────────────────┘
              │                      │
      ┌───────▼──────┐      ┌───────▼──────────┐
      │   Speech     │      │   LangGraph      │
      │  Processor   │      │   Agent          │
      │ (STT/TTS)    │      └───────┬──────────┘
      └───────┬──────┘              │
              │              ┌───────▼──────────┐
              │              │   Multi-Model    │
              │              │   LLM Provider   │
              │              │ (OpenAI/Claude/  │
              │              │    Gemini)       │
              │              └──────────────────┘
              │
      ┌───────▼──────────────────────────────┐
      │   Form Validator & State Manager     │
      └──────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- pip or poetry for dependency management
- API keys for at least one LLM provider (OpenAI, Anthropic, or Google)

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd TalkToFillAIAgent
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment variables**
```bash
cp .env.example .env
# Edit .env and add your API keys
```

**Minimum required configuration:**
```env
# Choose your preferred LLM provider
LLM_PROVIDER=openai

# Add corresponding API key
OPENAI_API_KEY=sk-your-key-here

# Optional: Configure speech providers
STT_PROVIDER=openai
TTS_PROVIDER=openai
```

5. **Start the server**
```bash
python -m src.api
```

The server will start at `http://localhost:8000`

6. **Test the API**
```bash
# In another terminal
python examples/test_client.py
```

## 📖 Usage

### Creating a Form Schema

Define your form in JSON format:

```json
{
  "form_id": "contact_form",
  "form_name": "Contact Form",
  "description": "Get in touch with us",
  "fields": [
    {
      "id": "name",
      "label": "Full Name",
      "type": "text",
      "required": true,
      "voice_hints": "What's your name?"
    },
    {
      "id": "email",
      "label": "Email",
      "type": "email",
      "required": true,
      "voice_hints": "What's your email address?"
    },
    {
      "id": "message",
      "label": "Message",
      "type": "textarea",
      "required": true,
      "voice_hints": "What would you like to tell us?"
    }
  ]
}
```

### Using the API

#### 1. Create a Session

```python
import requests
import json

# Load form schema
with open("my_form.json") as f:
    form_schema = json.load(f)

# Create session
response = requests.post(
    "http://localhost:8000/sessions",
    json={"form_schema": form_schema}
)
data = response.json()
session_id = data["session_id"]
print(data["welcome_message"])
```

#### 2. Send Text Input

```python
response = requests.post(
    f"http://localhost:8000/sessions/{session_id}/text",
    json={
        "session_id": session_id,
        "text": "My name is John Doe and my email is john@example.com"
    }
)
data = response.json()
print(data["message"])  # Agent's response
print(f"Completion: {data['completion_percentage']}%")
```

#### 3. Send Voice Input

```python
with open("audio.wav", "rb") as audio_file:
    response = requests.post(
        f"http://localhost:8000/sessions/{session_id}/voice",
        files={"audio": audio_file},
        data={"language": "en-US"}
    )
data = response.json()
print(data["message"])
# Audio response available in data["audio"] (base64 encoded)
```

#### 4. Get Form State

```python
response = requests.get(
    f"http://localhost:8000/sessions/{session_id}/form-state"
)
form_state = response.json()
print(json.dumps(form_state, indent=2))
```

## 🔧 Configuration

### LLM Provider Configuration

#### OpenAI (Default)
```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o-mini
OPENAI_TEMPERATURE=0.7
```

#### Anthropic Claude
```env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-your-key-here
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
ANTHROPIC_TEMPERATURE=0.7
```

#### Google Gemini
```env
LLM_PROVIDER=google
GOOGLE_API_KEY=your-key-here
GOOGLE_MODEL=gemini-2.0-flash-exp
GOOGLE_TEMPERATURE=0.7
```

### Speech Processing Configuration

#### Speech-to-Text
```env
STT_PROVIDER=openai  # Options: openai, google, whisper-local
STT_LANGUAGE=en-US
```

#### Text-to-Speech
```env
TTS_PROVIDER=openai  # Options: openai, google, gtts
TTS_VOICE=alloy      # OpenAI voices: alloy, echo, fable, onyx, nova, shimmer
```

## 📚 API Documentation

Once the server is running, visit:
- **Interactive API Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Main Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/sessions` | POST | Create a new form-filling session |
| `/sessions/{id}` | GET | Get session information |
| `/sessions/{id}/text` | POST | Process text input |
| `/sessions/{id}/voice` | POST | Process voice input |
| `/sessions/{id}/form-state` | GET | Get current form state |
| `/sessions/{id}/conversation` | GET | Get conversation history |
| `/sessions/{id}` | DELETE | Delete a session |

## 🎯 Examples

### Railway Booking Example

```python
from examples.test_client import FormFillingClient

client = FormFillingClient()
client.create_session("examples/railway_booking_form.json")

# Natural conversation
client.send_text("I want to book a train from Delhi to Mumbai")
client.send_text("Next Friday, 2 passengers")
client.send_text("AC 2-Tier class with window seats")
client.send_text("My email is user@example.com and phone is 9876543210")

# Check completion
form_state = client.get_form_state()
print(f"Form completion: {form_state['completion_percentage']}%")
```

### Job Application Example

```python
client = FormFillingClient()
client.create_session("examples/job_application_form.json")

# Multi-field extraction
client.send_text(
    "Hi, I'm Sarah Johnson applying for Software Engineer. "
    "I have 5 years of experience, Master's degree, "
    "currently in San Francisco. "
    "Email: sarah@example.com, Phone: 555-0123"
)

# Check what got filled
form_state = client.get_form_state()
```

## 🧪 Testing

Run the test suite:

```bash
# Start the server first
python -m src.api

# In another terminal, run tests
python examples/test_client.py
```

## 🔒 Production Deployment

### Using Redis for Session Management

1. Install and start Redis:
```bash
# Using Docker
docker run -d -p 6379:6379 redis:alpine

# Or install locally
brew install redis  # macOS
sudo apt-get install redis-server  # Ubuntu
```

2. Update configuration:
```env
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

3. The system will automatically use Redis when available.

### Docker Deployment

```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["python", "-m", "src.api"]
```

```bash
docker build -t voice-form-agent .
docker run -p 8000:8000 --env-file .env voice-form-agent
```

## 🛠️ Advanced Features

### Custom Validation Rules

```json
{
  "id": "age",
  "label": "Age",
  "type": "number",
  "required": true,
  "validation": {
    "min_value": 18,
    "max_value": 100,
    "hints": ["Must be 18 or older"]
  }
}
```

### Conditional Fields

```json
{
  "id": "other_reason",
  "label": "Please specify",
  "type": "text",
  "required": true,
  "depends_on": {
    "field": "reason",
    "condition": "equals",
    "value": "Other"
  }
}
```

### Voice Aliases

```json
{
  "id": "class",
  "type": "select",
  "options": ["Economy", "Business", "First Class"],
  "voice_aliases": {
    "Economy": ["economy", "basic", "normal", "coach"],
    "Business": ["business", "premium"],
    "First Class": ["first class", "first", "luxury"]
  }
}
```

## 📊 Monitoring & Logging

The system includes comprehensive logging:

```python
import logging
logging.basicConfig(level=logging.INFO)
```

Logs include:
- Session creation/deletion
- User input processing
- LLM interactions
- Validation errors
- Speech processing events

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

- **LangChain & LangGraph** for the agentic framework
- **FastAPI** for the excellent API framework
- **OpenAI**, **Anthropic**, and **Google** for LLM APIs
- All contributors to this project

## 📞 Support

For issues, questions, or contributions:
- Open an issue on GitHub
- Check the documentation at `/docs` endpoint
- Review example code in `examples/`

## 🗺️ Roadmap

- [ ] WebSocket support for real-time streaming
- [ ] Frontend UI components (React/Vue)
- [ ] Multi-language support
- [ ] Voice authentication
- [ ] Offline mode with local models
- [ ] Form analytics dashboard
- [ ] Integration with popular form builders

---

**Built with ❤️ using Python, LangGraph, and Multi-Model LLMs**