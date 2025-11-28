"""
Data validation and cleaning utilities for invoice data
"""
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


def clean_item_name(name: str) -> str:
    """
    Clean item name by removing invalid characters

    Args:
        name: Raw item name

    Returns:
        Cleaned item name
    """
    if not isinstance(name, str):
        return str(name)

    # Replace control characters with spaces
    cleaned = ''.join(char if char.isprintable() or char in ['\n', '\t'] else ' ' for char in name)

    # Replace newlines and tabs with spaces
    cleaned = cleaned.replace('\n', ' ').replace('\t', ' ')

    # Replace multiple spaces with single space
    cleaned = ' '.join(cleaned.split())

    # Trim
    cleaned = cleaned.strip()

    return cleaned


def validate_numeric_field(value: Any, field_name: str, default: float = 0.0) -> float:
    """
    Validate and convert numeric field

    Args:
        value: Value to validate
        field_name: Name of the field (for logging)
        default: Default value if validation fails

    Returns:
        Validated float value
    """
    try:
        # Handle strings with commas
        if isinstance(value, str):
            value = value.replace(',', '')

        float_value = float(value)

        # Check for negative values (shouldn't happen in invoices)
        if float_value < 0:
            logger.warning(f"{field_name} is negative: {float_value}, using absolute value")
            float_value = abs(float_value)

        return float_value

    except (ValueError, TypeError) as e:
        logger.warning(f"Invalid {field_name}: {value}, using default {default}. Error: {e}")
        return default


def validate_bill_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and clean a single bill item

    Args:
        item: Raw bill item data

    Returns:
        Validated and cleaned bill item
    """
    validated = {}

    # Clean item name
    validated['item_name'] = clean_item_name(item.get('item_name', 'Unknown Item'))

    # Validate numeric fields
    validated['item_quantity'] = validate_numeric_field(
        item.get('item_quantity', 1.0),
        'item_quantity',
        default=1.0
    )

    validated['item_rate'] = validate_numeric_field(
        item.get('item_rate', 0.0),
        'item_rate',
        default=0.0
    )

    validated['item_amount'] = validate_numeric_field(
        item.get('item_amount', 0.0),
        'item_amount',
        default=0.0
    )

    # Validate calculation: item_amount should be item_quantity * item_rate
    # Allow for small rounding errors
    expected_amount = validated['item_quantity'] * validated['item_rate']
    actual_amount = validated['item_amount']

    if abs(expected_amount - actual_amount) > 0.01 and expected_amount > 0:
        logger.debug(
            f"Amount mismatch for '{validated['item_name']}': "
            f"expected {expected_amount}, got {actual_amount}"
        )
        # Use the provided amount if available, otherwise calculate
        if actual_amount == 0.0 and expected_amount > 0:
            validated['item_amount'] = expected_amount

    return validated


def validate_page_type(page_type: str) -> str:
    """
    Validate page type

    Args:
        page_type: Raw page type

    Returns:
        Valid page type
    """
    valid_types = ["Bill Detail", "Final Bill", "Pharmacy"]

    if page_type in valid_types:
        return page_type

    # Try case-insensitive match
    for valid_type in valid_types:
        if page_type.lower() == valid_type.lower():
            return valid_type

    # Default to "Bill Detail"
    logger.warning(f"Invalid page_type: {page_type}, defaulting to 'Bill Detail'")
    return "Bill Detail"


def validate_and_clean_invoice_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and clean entire invoice data structure

    Args:
        data: Raw invoice data

    Returns:
        Validated and cleaned invoice data
    """
    validated = {
        "pagewise_line_items": []
    }

    if not isinstance(data, dict):
        logger.error(f"Invalid data type: {type(data)}, expected dict")
        return validated

    pagewise_items = data.get("pagewise_line_items", [])

    if not isinstance(pagewise_items, list):
        logger.error(f"Invalid pagewise_line_items type: {type(pagewise_items)}, expected list")
        return validated

    for page_data in pagewise_items:
        if not isinstance(page_data, dict):
            logger.warning(f"Skipping invalid page data: {type(page_data)}")
            continue

        validated_page = {
            "page_no": str(page_data.get("page_no", "1")),
            "page_type": validate_page_type(page_data.get("page_type", "Bill Detail")),
            "bill_items": []
        }

        bill_items = page_data.get("bill_items", [])

        if not isinstance(bill_items, list):
            logger.warning(f"Invalid bill_items type: {type(bill_items)}, expected list")
            bill_items = []

        for item in bill_items:
            if not isinstance(item, dict):
                logger.warning(f"Skipping invalid bill item: {type(item)}")
                continue

            validated_item = validate_bill_item(item)

            # Only add items with valid names
            if validated_item['item_name'] and validated_item['item_name'] != 'Unknown Item':
                validated_page['bill_items'].append(validated_item)

        # Only add pages with items
        if validated_page['bill_items']:
            validated['pagewise_line_items'].append(validated_page)

    return validated


def remove_duplicate_items(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove duplicate items from invoice data
    
    IMPORTANT: Only removes duplicates WITHIN each page, not across pages.
    This preserves legitimate repeated charges across different pages.
    
    Args:
        data: Invoice data
        
    Returns:
        Data with duplicates removed (per page only)
    """
    cleaned_data = {
        "pagewise_line_items": []
    }
    
    for page_data in data.get("pagewise_line_items", []):
        # Track duplicates PER PAGE only
        seen_items_on_page = set()
        
        cleaned_page = {
            "page_no": page_data["page_no"],
            "page_type": page_data["page_type"],
            "bill_items": []
        }
        
        for item in page_data.get("bill_items", []):
            # Create a signature for the item
            item_signature = (
                item['item_name'].lower().strip(),
                item['item_quantity'],
                item['item_rate'],
                item['item_amount']
            )
            
            # Only check for duplicates within THIS page
            if item_signature not in seen_items_on_page:
                seen_items_on_page.add(item_signature)
                cleaned_page['bill_items'].append(item)
            else:
                logger.debug(f"Removing duplicate item on page {page_data['page_no']}: {item['item_name']}")
        
        if cleaned_page['bill_items']:
            cleaned_data['pagewise_line_items'].append(cleaned_page)
    
    return cleaned_data
