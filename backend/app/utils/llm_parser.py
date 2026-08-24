import json
import re


def extract_json(text: str):
    """
    Safely extract a JSON value (list or dict) from an LLM response.

    Handles:
    - Raw JSON
    - JSON wrapped in ```json ... ``` code fences
    - Leading/trailing prose around the JSON
    """
    text = text.strip()

    # 1. Try to parse as-is
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2. Strip markdown code fences and retry
    code_block = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if code_block:
        try:
            return json.loads(code_block.group(1))
        except json.JSONDecodeError:
            pass

    # 3. Find the first JSON array in the text
    array_match = re.search(r"\[[\s\S]*\]", text)
    if array_match:
        try:
            return json.loads(array_match.group())
        except json.JSONDecodeError:
            pass

    # 4. Find the first JSON object in the text
    obj_match = re.search(r"\{[\s\S]*\}", text)
    if obj_match:
        try:
            return json.loads(obj_match.group())
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not extract JSON from LLM response:\n{text[:300]}")
