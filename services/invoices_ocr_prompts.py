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

CRITICAL INSTRUCTIONS:

1. EXTRACT EVERY SINGLE LINE ITEM:
   - Extract EVERY row from the invoice table, even if items have the same name
   - DO NOT skip or merge items with identical names
   - Each row in the table is a SEPARATE billable item that must be extracted
   - If you see 10 rows of "IP CONSULTATION CHARGES", extract ALL 10 as separate items
   - Count each row individually - do NOT summarize or combine

2. PAGEWISE EXTRACTION:
   - Track which page number each line item appears on
   - Page numbers should be strings (e.g., "1", "2", "3")
   - Group all items by their page number
   - Classify each page type as one of: "Bill Detail", "Final Bill", or "Pharmacy"
   - NEVER use null for page_type - always choose one of the three options

3. FIELD EXTRACTION:
   For each line item, extract these exact fields:
   - item_name: The description or name of the item/service (preserve exactly as shown)
   - item_quantity: The quantity (as a number, e.g., 1.0, 2.5, 10.0)
   - item_rate: The unit price or rate (as a number, e.g., 100.00, 250.50)
   - item_amount: The total amount for this line item (quantity × rate)

4. DATA FORMATTING:
   - Remove currency symbols (₹, $, etc.) from all numeric values
   - Convert all amounts to decimal numbers (e.g., 1,000.00 → 1000.00)
   - Keep quantities as decimal numbers (e.g., 3 → 3.0, 2.5 → 2.5)
   - Preserve full item names/descriptions as they appear
   - IMPORTANT: Ensure all item_name strings are properly formatted for JSON (no unescaped quotes or newlines)

5. CALCULATION RULES:
   - item_amount should equal item_quantity × item_rate
   - If only item_amount is visible, and quantity is 1, then item_rate = item_amount
   - Extract ALL line items from ALL pages

6. WHAT TO EXTRACT:
   - Extract individual line items (products, services, charges, fees, etc.)
   - Extract EVERY row, even if the item name repeats
   - DO NOT extract sub-totals, tax totals, or grand totals as line items
   - Only extract actual billable items from the main table

7. MULTI-PAGE HANDLING:
   - If an invoice spans multiple pages, extract items from ALL pages
   - Assign correct page numbers to each item
   - Do not skip any pages

8. REPEATED ITEMS - IMPORTANT RULES:
   - Items are ONLY duplicates if ALL fields match exactly: name, quantity, rate, AND amount
   - If ANY field is different, treat as SEPARATE items:
     * Same name but different quantity → SEPARATE items
     * Same name but different rate → SEPARATE items
     * Same name but different amount → SEPARATE items
   - Example: "IP CONSULTATION CHARGES" appears 10 times with same values → Extract ALL 10
   - Example: "Medicine A" with qty=1, rate=100 AND "Medicine A" with qty=2, rate=100 → Extract BOTH
   - Each row in the invoice table = one item in your output
   - Do NOT merge or summarize items, even if they have the same name

9. JSON OUTPUT REQUIREMENTS:
   - Return ONLY valid JSON - no markdown, no code blocks
   - Ensure all strings are properly escaped
   - All numeric values must be valid numbers (not strings)
   - page_type must be one of: "Bill Detail", "Final Bill", "Pharmacy" (NEVER null)

CONCRETE EXAMPLE - How to extract repeated items:

If you see this invoice table:
```
Item Name                  | Qty | Rate    | Amount
IP CONSULTATION CHARGES    | 1   | 1000.00 | 1000.00
IP CONSULTATION CHARGES    | 1   | 1000.00 | 1000.00
IP CONSULTATION CHARGES    | 1   | 1000.00 | 1000.00
```

You MUST return:
```json
{
  "bill_items": [
    {"item_name": "IP CONSULTATION CHARGES", "item_quantity": 1.0, "item_rate": 1000.0, "item_amount": 1000.0},
    {"item_name": "IP CONSULTATION CHARGES", "item_quantity": 1.0, "item_rate": 1000.0, "item_amount": 1000.0},
    {"item_name": "IP CONSULTATION CHARGES", "item_quantity": 1.0, "item_rate": 1000.0, "item_amount": 1000.0}
  ]
}
```

DO NOT return just one item! Extract each row separately.

REMEMBER: Extract EVERY row from the invoice table. If you see 50 line items, return 50 items. Do not skip or merge anything.

FINAL CHECK BEFORE RESPONDING:
1. Count the total number of rows in ALL invoice tables across ALL pages
2. Count the number of items in your JSON response
3. These numbers MUST be equal - if they're not, you've skipped items
4. Go back and add any missing items before responding

Extract all line items and return them in the specified JSON format."""

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
