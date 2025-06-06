# awesome_caller_boi

A small Python package that exposes a FastAPI router to connect Twilio’s voice streaming directly to the OpenAI realtime API (GPT-4o). It handles incoming calls, establishes the WebSocket media stream with Twilio, forwards audio to OpenAI, and sends back OpenAI’s audio response to the caller.

## Features

- Provides a FastAPI router for Twilio voice webhooks.
- Streams inbound audio from Twilio to OpenAI in real time.
- Encodes and forwards OpenAI’s audio responses back to Twilio.
- Automatically handles speech interruptions (caller starts speaking mid-response).
- Easy to configure with your own `get_system_message()` and `get_system_greeting()` callbacks.
- Put your OpenAi key in your enviornment variables and call it OPENAI_API_KEY

## Installation

From PyPI (once published):
```bash
pip install awesome_caller_boi

## Usage Example 

from awesome_caller_boi.call_handler import create_call_router
from models.transcripts import Transcript

def my_middleware_fn(transcript: Transcript) -> dict:
    # extract name, order, etc., or send it to your database
    print("Got a finished call from:", transcript.phone_number)
    print("Full transcript text:", transcript.call_text)
    return {"status": "ok"}

app.include_router(
    create_call_router(
        get_system_message=my_system_message,
        get_system_greeting=my_system_greeting,
        voice="alloy",
        on_call_complete=my_middleware_fn
    )
)
