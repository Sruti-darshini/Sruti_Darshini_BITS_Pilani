"""
Dynamic prompt generation for invoice OCR
"""
from typing import Dict, Any


def generate_extraction_prompt() -> str:
    """
    Generate prompt for extracting pagewise line items from invoice

    Returns:
        Formatted prompt string
    """
    prompt = """You are an expert invoice data extraction system. Analyze the provided invoice images and extract ALL line items with their details.

CRITICAL: You MUST extract data from the invoice. Do NOT return empty results unless the invoice is completely blank.

IMPORTANT INSTRUCTIONS:

1. PAGEWISE EXTRACTION:
   - Track which page number each line item appears on
   - Page numbers should be strings (e.g., "1", "2", "3")
   - Group all items by their page number
   - Classify each page type as one of: "Bill Detail", "Final Bill", or "Pharmacy"
   - NEVER use null for page_type - always choose one of the three options
   - If unsure about page type, default to "Bill Detail"

2. FIELD EXTRACTION:
   For each line item, extract these exact fields:
   - item_name: The description or name of the item/service (preserve exactly as shown, replace any quotes with single quotes)
   - item_quantity: The quantity (as a number, e.g., 1.0, 2.5, 10.0) - if not visible, use 1.0
   - item_rate: The unit price or rate (as a number, e.g., 100.00, 250.50)
   - item_amount: The total amount for this line item (quantity × rate)

3. DATA FORMATTING:
   - Remove currency symbols (₹, $, etc.) from all numeric values
   - Convert all amounts to decimal numbers (e.g., 1,000.00 → 1000.00, remove commas)
   - Keep quantities as decimal numbers (e.g., 3 → 3.0, 2.5 → 2.5)
   - Preserve full item names/descriptions as they appear
   - CRITICAL: Replace double quotes (") in item names with single quotes (') to avoid JSON errors
   - Replace newlines in item names with spaces
   - Remove any control characters from item names

4. CALCULATION RULES:
   - item_amount should equal item_quantity × item_rate
   - If only item_amount is visible, and quantity is 1, then item_rate = item_amount
   - Extract ALL line items from ALL pages
   - Be thorough - don't skip items even if the format is unusual

5. WHAT TO EXTRACT:
   - Extract individual line items (products, services, charges, fees, tests, procedures, etc.)
   - DO NOT extract sub-totals, tax totals, or grand totals as line items
   - Only extract actual billable items
   - Include items even if some fields are missing (use reasonable defaults)

6. MULTI-PAGE HANDLING:
   - If an invoice spans multiple pages, extract items from ALL pages
   - Assign correct page numbers to each item
   - Do not duplicate items across pages
   - Process each page thoroughly

7. JSON OUTPUT REQUIREMENTS:
   - Return ONLY valid, well-formed JSON
   - NO markdown formatting, NO code blocks, NO extra text
   - Ensure all strings are properly escaped and complete
   - All numeric values must be valid numbers (not strings)
   - page_type must be one of: "Bill Detail", "Final Bill", "Pharmacy" (NEVER null)
   - NEVER leave strings unterminated
   - Ensure all opening braces { and brackets [ have matching closing braces } and brackets ]

8. HANDLING LARGE INVOICES:
   - For invoices with many items, ensure you extract ALL items
   - Don't truncate your output - complete the full JSON structure
   - If you encounter any items, make sure to close all JSON objects properly

Extract all line items and return them in the specified JSON format. Double-check that your JSON is valid and complete before responding."""

    return prompt


def get_json_schema() -> Dict[str, Any]:
    """
    Get JSON schema for structured LLM output
    
    Returns:
        JSON schema dictionary
    """
    schema = {
        "type": "object",
        "properties": {
            "pagewise_line_items": {
                "type": "array",
                "description": "Line items grouped by page number",
                "items": {
                    "type": "object",
                    "properties": {
                        "page_no": {
                            "type": "string",
                            "description": "Page number as string"
                        },
                        "page_type": {
                            "type": "string",
                            "enum": ["Bill Detail", "Final Bill", "Pharmacy"],
                            "description": "Type of page - must be one of: Bill Detail, Final Bill, or Pharmacy"
                        },
                        "bill_items": {
                            "type": "array",
                            "description": "All line items on this page",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "item_name": {
                                        "type": "string",
                                        "description": "Item description/name"
                                    },
                                    "item_quantity": {
                                        "type": "number",
                                        "description": "Quantity"
                                    },
                                    "item_rate": {
                                        "type": "number",
                                        "description": "Unit price/rate"
                                    },
                                    "item_amount": {
                                        "type": "number",
                                        "description": "Total amount for this line item"
                                    }
                                },
                                "required": ["item_name", "item_quantity", "item_rate", "item_amount"]
                            }
                        }
                    },
                    "required": ["page_no", "page_type", "bill_items"]
                }
            }
        },
        "required": ["pagewise_line_items"]
    }
    
    return schema
