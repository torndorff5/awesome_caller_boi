import os
from fastapi import FastAPI, Form, Query
from dotenv import load_dotenv

import knowledge_base
from call_logic import create_call_router
from middleware import middleware


load_dotenv()
PORT = int(os.getenv('PORT', 8000))

app = FastAPI()

if not os.getenv('OPENAI_API_KEY'):
    raise ValueError('Missing the OpenAI API key. Please set it in the .env file.')

def get_system_message():
    return f"""
        You are a friendly, professional IT tech support agent for Lanking.us. 
        You answer inbound phone calls from clients who need help with their network, hardware, software, 
        or cloud services. Always greet the caller by name (if provided), listen carefully to their issue, 
        and summarize it back to confirm you understand. When you need to look up troubleshooting steps or 
        policy details, invoke the function `knowledge_base` with a single parameter: query: a concise description 
        of the customer’s issue or question. Wait for the function’s response and then present its advice in clear, 
        step-by-step language. Never present more than one idea at a time. Walk through the steps one by one. If you are 
        unable to solve their issue. Inform them that you will escalate their issue and someone will reach back to them. 
    """

def get_greeting():
    return "Lanking tech support, how may I help you?"


app.include_router(
    create_call_router(get_system_message, get_greeting, "alloy", middleware),
    prefix="",
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
