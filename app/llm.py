# app/services/llm.py
import json
from typing import Dict

# TODO: plug in your OpenAI or other LLM client here.

def generate_daily_brief_text(context: Dict) -> str:
    """
    Given the context dict, call the LLM with:
    - system prompt (analyst persona)
    - user prompt (template) including the JSON
    Return markdown/plain text.
    """
    # Pseudocode:
    # system_message = ...
    # user_message = ...
    # response = client.chat.completions.create(...)
    # return response.choices[0].message.content
    raise NotImplementedError("Implement LLM call here.")
