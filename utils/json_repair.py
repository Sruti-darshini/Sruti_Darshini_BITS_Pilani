"""
Robust JSON repair utilities for handling malformed LLM responses
"""
import json
import re
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def clean_json_string(text: str) -> str:
    """
    Clean JSON string by removing markdown and extra whitespace

    Args:
        text: Raw text that may contain JSON

    Returns:
        Cleaned JSON string
    """
    # Remove markdown code blocks
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)

    # Remove leading/trailing whitespace
    text = text.strip()

    return text


def extract_json_object(text: str) -> Optional[str]:
    """
    Extract JSON object from text using pattern matching

    Args:
        text: Text that may contain JSON

    Returns:
        Extracted JSON string or None
    """
    # Try to find the outermost JSON object
    brace_count = 0
    start_idx = -1

    for i, char in enumerate(text):
        if char == '{':
            if start_idx == -1:
                start_idx = i
            brace_count += 1
        elif char == '}':
            brace_count -= 1
            if brace_count == 0 and start_idx != -1:
                return text[start_idx:i+1]

    return None


def fix_truncated_json(text: str) -> str:
    """
    Attempt to fix truncated JSON by closing open structures

    Args:
        text: Potentially truncated JSON string

    Returns:
        Repaired JSON string with closed structures
    """
    # Remove markdown code blocks first
    text = clean_json_string(text)

    # Count open/close braces and brackets
    open_braces = text.count('{')
    close_braces = text.count('}')
    open_brackets = text.count('[')
    close_brackets = text.count(']')

    # Find the last valid position
    # Look for the last complete item before truncation
    lines = text.split('\n')

    # Find the last line that looks complete (ends with , or } or ])
    last_valid_line = -1
    for i in range(len(lines) - 1, -1, -1):
        line = lines[i].strip()
        if line.endswith(',') or line.endswith('}') or line.endswith(']') or line.endswith('},') or line.endswith('],'):
            last_valid_line = i
            break

    # If we found a valid stopping point, truncate there
    if last_valid_line > 0:
        text = '\n'.join(lines[:last_valid_line + 1])

        # Remove trailing comma if present
        if text.rstrip().endswith(','):
            text = text.rstrip()[:-1]

    # Now close any open structures
    open_braces = text.count('{')
    close_braces = text.count('}')
    open_brackets = text.count('[')
    close_brackets = text.count(']')

    # Close brackets first, then braces
    while close_brackets < open_brackets:
        text += '\n]'
        close_brackets += 1

    while close_braces < open_braces:
        text += '\n}'
        close_braces += 1

    return text


def fix_unterminated_strings(text: str) -> str:
    """
    Attempt to fix unterminated strings in JSON

    Args:
        text: JSON string with potential unterminated strings

    Returns:
        Repaired JSON string
    """
    # First try to fix truncation
    text = fix_truncated_json(text)

    # Count quotes to detect unterminated strings
    # This is a simple heuristic and may not work for all cases
    lines = text.split('\n')
    fixed_lines = []

    for line in lines:
        # Skip if line is just braces or brackets
        if line.strip() in ['{', '}', '[', ']', ',']:
            fixed_lines.append(line)
            continue

        # Check if line has unterminated string (odd number of unescaped quotes)
        # This is a simplification - proper fix would need a full parser
        quote_count = line.count('"') - line.count('\\"')

        if quote_count % 2 != 0:
            # Try to close the string
            if line.rstrip().endswith(','):
                line = line.rstrip()[:-1] + '\",'
            elif line.rstrip().endswith('}') or line.rstrip().endswith(']'):
                last_quote = line.rfind('"')
                if last_quote > 0:
                    line = line[:last_quote] + '\"' + line[last_quote+1:]
            else:
                # Just close the string
                line = line.rstrip() + '\"'

        fixed_lines.append(line)

    return '\n'.join(fixed_lines)


def escape_control_characters(text: str) -> str:
    """
    Escape unescaped control characters in JSON string values

    Args:
        text: JSON string

    Returns:
        JSON with escaped control characters
    """
    # Replace unescaped newlines in strings
    # This is a simple approach - may need refinement
    text = re.sub(r'(?<!\\)\n(?![}\]])', '\\\\n', text)
    text = re.sub(r'(?<!\\)\r', '\\\\r', text)
    text = re.sub(r'(?<!\\)\t', '\\\\t', text)

    return text


def repair_json(text: str, max_attempts: int = 5) -> Optional[Dict[str, Any]]:
    """
    Attempt to repair and parse malformed JSON with multiple strategies

    Args:
        text: Raw JSON string (potentially malformed)
        max_attempts: Maximum number of repair attempts

    Returns:
        Parsed JSON dict or None if all attempts fail
    """
    if not text or not text.strip():
        logger.warning("Empty JSON string provided")
        return None

    # Strategy 1: Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.debug(f"Direct parse failed: {e}")

    # Strategy 2: Clean and try again
    try:
        cleaned = clean_json_string(text)
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.debug(f"Cleaned parse failed: {e}")

    # Strategy 3: Extract JSON object and parse
    try:
        extracted = extract_json_object(text)
        if extracted:
            return json.loads(extracted)
    except json.JSONDecodeError as e:
        logger.debug(f"Extracted parse failed: {e}")

    # Strategy 4: Fix unterminated strings
    try:
        fixed = fix_unterminated_strings(text)
        return json.loads(fixed)
    except json.JSONDecodeError as e:
        logger.debug(f"Unterminated string fix failed: {e}")

    # Strategy 5: Escape control characters
    try:
        escaped = escape_control_characters(text)
        return json.loads(escaped)
    except json.JSONDecodeError as e:
        logger.debug(f"Control character escape failed: {e}")

    # Strategy 6: Combined approach
    try:
        text_cleaned = clean_json_string(text)
        text_extracted = extract_json_object(text_cleaned)
        if text_extracted:
            text_fixed = fix_unterminated_strings(text_extracted)
            text_escaped = escape_control_characters(text_fixed)
            return json.loads(text_escaped)
    except json.JSONDecodeError as e:
        logger.debug(f"Combined repair failed: {e}")

    # Strategy 7: Use json5 if available (more lenient parser)
    try:
        import json5
        return json5.loads(text)
    except (ImportError, Exception) as e:
        logger.debug(f"json5 parse failed: {e}")

    # If all strategies fail, log and return None
    logger.error(f"All JSON repair strategies failed. First 500 chars: {text[:500]}")
    return None


def validate_invoice_structure(data: Dict[str, Any]) -> bool:
    """
    Validate that the JSON has the expected invoice structure

    Args:
        data: Parsed JSON dict

    Returns:
        True if structure is valid, False otherwise
    """
    if not isinstance(data, dict):
        return False

    if "pagewise_line_items" not in data:
        return False

    if not isinstance(data["pagewise_line_items"], list):
        return False

    # Check each page item
    for page_item in data["pagewise_line_items"]:
        if not isinstance(page_item, dict):
            return False

        required_fields = ["page_no", "page_type", "bill_items"]
        if not all(field in page_item for field in required_fields):
            return False

        if not isinstance(page_item["bill_items"], list):
            return False

        # Check each bill item
        for bill_item in page_item["bill_items"]:
            if not isinstance(bill_item, dict):
                return False

            required_item_fields = ["item_name", "item_quantity", "item_rate", "item_amount"]
            if not all(field in bill_item for field in required_item_fields):
                return False

    return True


def get_empty_invoice_structure() -> Dict[str, Any]:
    """
    Get an empty but valid invoice structure

    Returns:
        Empty invoice structure dict
    """
    return {
        "pagewise_line_items": []
    }
