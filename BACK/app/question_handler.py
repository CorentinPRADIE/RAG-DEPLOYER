from pydantic import BaseModel
from app.utils.logger import logger
import time
import ollama

def print_conversation(conversation):
    """Print the conversation in a custom format."""
    for msg in conversation:
        print(f"{msg['role']} : {msg['content']}")




def generate_response(conversation, model_name):
    """Generate a response from the LLM using the conversation as input."""
    # Verify that `conversation` is in the correct format
    if not isinstance(conversation, list) or not all(
        isinstance(msg, dict) and 'role' in msg and 'content' in msg
        for msg in conversation
    ):
        logger.error("Invalid format for `conversation`: Expected list of dictionaries with `role` and `content` fields.")
        raise ValueError("Invalid format for `conversation` passed to ollama.chat")

    # Log the conversation structure in a concise format using pprint
    logger.info("Sending conversation to ollama.chat:")
    print_conversation(conversation)

    # Proceed to call ollama.chat
    try:
        start_time = time.time()
        response = ollama.chat(model=model_name, messages=conversation)
        generation_duration = time.time() - start_time
        response_text = response.get("message", {}).get("content", "")
        return response_text, generation_duration
    except ollama._types.ResponseError as e:
        logger.error(f"ResponseError from ollama.chat: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during ollama.chat: {e}")