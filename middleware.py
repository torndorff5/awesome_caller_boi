import json
import datetime
import os
from dotenv import load_dotenv
from openai import OpenAI
from menu import menu
from models.transcripts import Transcript

load_dotenv()

# Ensure your OpenAI API key is set:
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
variable_list = os.getenv("OPENAI_VARIABLES")
variable_json = os.getenv("OPENAI_VARIABLES_JSON")
middleware_system_prompt = os.getenv("middleware_system_prompt")

def middleware(full_transcript: Transcript) -> dict:
    f"""
    Given a completed call transcript as a single string, call OpenAI ChatCompletion
    to extract:
    {variable_list}

    Immediately generate createdAt as the current UTC timestamp in ISO-8601 format.

    Returns:
    {variable_json}
    """
    system_prompt = middleware_system_prompt

    user_prompt = f"Here is the call transcript:\n```\n{full_transcript.call_text}\n```"

    completion = client.chat.completions.create(
        model="o4-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt}
        ],
    )

    assistant_reply = completion.choices[0].message.content

    try:
        parsed = json.loads(assistant_reply)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse JSON from OpenAI response:\n{assistant_reply}") from e

    now_utc = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
    created_at_iso = now_utc.isoformat().replace("+00:00", "Z")

    print(parsed)