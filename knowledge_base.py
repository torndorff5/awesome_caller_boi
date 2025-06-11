import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
vector_store_id = os.getenv("VECTOR_STORE_ID")# get vector store, but practice with a hello world function in the realtime api.
client = OpenAI(api_key=api_key)

def knowledge_base(input_text: str) -> str:
    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": os.getenv("SYSTEM_INSTRUCTIONS"),
                    }
                ]
            },
            {
                "role": "user",
                "content": input_text
            }
        ],
        text={
            "format": {
                "type": "text"
            }
        },
        reasoning={},
        tools=[
            {
                "type": "file_search",
                "vector_store_ids": [vector_store_id]
            }
        ],
        temperature=1,
        max_output_tokens=2048,
        top_p=1,
        store=True
    )
    # Extract and return the text content from the response
    return get_text_from_response(response)


def get_text_from_response(response) -> str:
    # Check if response has output attribute and is non-empty
    if not hasattr(response, "output") or not response.output:
        return "No output in response."

    # Find the first ResponseOutputMessage in output
    output_message = next((item for item in response.output if getattr(item, "type", "") == "message"), None)
    if output_message is None:
        return "No message output found."

    # The content is a list with ResponseOutputText objects
    content_list = getattr(output_message, "content", [])
    if not content_list:
        return "No content found in message."

    # Extract text from first ResponseOutputText (usually the answer text)
    first_content = content_list[0]
    text = getattr(first_content, "text", None)
    if not text:
        return "No text found in content."

    # text is a string, return it
    return text