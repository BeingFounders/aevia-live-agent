<p align="center">
  <img src="aevia.png" alt="Aevia Image"/>
</p>

# Aevia Live Agent

A live agent implementation using CDP (Chaindesk Protocol), LangChain, and Telegram for automated user status verification.

## Project Structure

- `app_agent.py`: Main agent implementation using LangChain and FastAPI endpoints
- `telethon_api.py`: Telegram client wrapper for message handling
- `protocol_api.py`: Protocol API implementation for handling different status protocols
- `requirements.txt`: Project dependencies

## Components

### Telegram API (telethon_api.py)
Handles Telegram messaging functionality:
- Message sending and receiving
- Image sharing
- Message history tracking
- Async communication with Telegram servers

### Protocol API (protocol_api.py)
Manages different protocol states:
- Alive Protocol: When user confirms they're okay
- Emergency Protocol: When user doesn't respond
- Dead Protocol: When user is confirmed deceased
- Endpoints for protocol management and status updates

## Setup

1. Create a virtual environment and activate it:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Configure environment variables in `.env`:

```bash
OPENAI_API_KEY=your-openai-key
API_ID=your-telegram-api-id
API_HASH=your-telegram-api-hash
```

## Dependencies

- telethon: Telegram client library
- langchain: LLM framework
- openai: OpenAI API integration
- fastapi: API framework
- python-dotenv: Environment management
- httpx: Async HTTP client
- uvicorn: ASGI server

## Running the Services

Start the main agent:

```bash
uvicorn app_agent:app --reload --port 8000
```

Start the protocol API:

```bash
uvicorn protocol_api:app --reload --port 8001
```

## API Endpoints

### Agent

- `POST /start_conversation_user`: Start a conversation with the user
- `POST /start_conversation_beneficiary`: Start a conversation with the beneficiary
- `POST /start_conversation_emergency`: Start a conversation with the emergency
- `POST /generate_memorial`: Generate a memorial message

### Protocol

- `POST /start_cron`: Start the cron job
- `POST /alive_protocol`: Confirm user is alive
- `POST /emergency_protocol`: Confirm user is in emergency
- `POST /dead_protocol`: Confirm user is deceased

