"""
Resilient JSON parsing and code-fence stripping for LLM outputs.
Handles reasoning models (like DeepSeek-R1 with <think> blocks) and free models.
"""

import json
import re
from typing import Any, Dict, Optional, Type, TypeVar
from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


def clean_llm_response(text: str) -> str:
    """Remove reasoning tags (e.g. <think>...</think>) and leading/trailing whitespace."""
    if not text:
        return ""
    # Strip DeepSeek-R1 thinking tokens
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    return cleaned.strip()


def extract_json_string(text: str) -> str:
    """Extract json substring, stripping markdown code fences or surrounding prose."""
    cleaned = clean_llm_response(text)
    
    # 1. Check for markdown code fences ```json ... ``` or ``` ... ```
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
    if fence_match:
        content = fence_match.group(1).strip()
        if content.startswith("{") and content.endswith("}"):
            return content

    # 2. Extract outermost matching curly braces { ... }
    first_brace = cleaned.find("{")
    last_brace = cleaned.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        return cleaned[first_brace : last_brace + 1].strip()

    return cleaned


def parse_and_validate_json(
    raw_text: str,
    target_schema: Optional[Type[T]] = None,
) -> tuple[Optional[Any], Optional[str]]:
    """
    Parse raw LLM response text into JSON and optionally validate against a Pydantic model.
    Returns: (parsed_object, error_message)
    """
    json_str = extract_json_string(raw_text)
    try:
        data = json.loads(json_str)
    except Exception as e:
        return None, f"JSONDecodeError: {str(e)} (Raw snippet: {json_str[:120]})"

    if target_schema:
        try:
            instance = target_schema.model_validate(data)
            return instance, None
        except ValidationError as e:
            return None, f"SchemaValidationError: {str(e)}"

    return data, None
