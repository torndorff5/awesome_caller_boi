import os
from fastapi import FastAPI, Form, Query
from dotenv import load_dotenv
from call_logic import create_call_router
from middleware import middleware


load_dotenv()
PORT = int(os.getenv('PORT', 8000))

app = FastAPI()

if not os.getenv('OPENAI_API_KEY'):
    raise ValueError('Missing the OpenAI API key. Please set it in the .env file.')

def get_system_message():
    return f"""
    You are a friendly, professional AI voice agent for Lanking. You work technical support for their customers
    who are gamers at one of Lankings many lounges. When people call in needing help with Lankings services, call the
    knowledge_base function to learn how to best help them. 
    """

def get_greeting():
    return "LanKing, how may I help you?"


app.include_router(
    create_call_router(get_system_message, get_greeting, "alloy", middleware),
    prefix="",
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
