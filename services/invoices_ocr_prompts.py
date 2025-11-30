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

⚠️ CRITICAL: READ THE TABLE CORRECTLY - MATCH COLUMNS PROPERLY ⚠️

STEP-BY-STEP EXTRACTION PROCESS:

STEP 1: UNDERSTAND THE TABLE STRUCTURE
Most invoices have columns in this order:
[S.No | Date | Code | Item Name/Description | Rate | Qty | Amount]

Or sometimes:
[Item Name | Qty | Rate | Amount]

Or pharmacy bills:
[HSN# | Batch | Exp | Description | Qty | Rate | DISC | Amount | GST%]

CRITICAL RULES FOR READING TABLES:
1. Read LEFT to RIGHT across each row
2. Match the CORRECT column for each field:
   - Item Name is usually the WIDEST column with text
   - Rate/Qty are usually shown as "X.XX x Y.YY" or in separate columns
   - Amount is usually the RIGHTMOST number
3. DO NOT mix up columns - if Rate is in column 4, Qty is in column 5, take values from those exact columns
4. For the Nth item, take the Nth rate, Nth quantity, and Nth amount

⚠️ SPECIAL: HANDLING POOR QUALITY SCANS ⚠️

If the invoice image is:
- Tilted/skewed
- Faint/low contrast
- Blurry
- Has crossed-out text or marks

DO THESE EXTRA CHECKS:

1. COUNT ROWS CAREFULLY:
   - Look for horizontal lines separating rows
   - Even if text is faint, you can see row structure
   - Count EVERY row, even if text is hard to read
   - Use row spacing/lines to detect all items

2. CHECK FOR SEQUENTIAL NUMBERS:
   - If there's an S.No column (1, 2, 3...), check for gaps
   - Missing number = missing row = you need to extract it
   - Example: You see 1, 2, 4, 5 → Row #3 is missing, look harder for it

3. LOOK FOR FAINT TEXT:
   - Some rows may have very faint text
   - Zoom in mentally on each row
   - Even if you can only read partial text, extract what you can
   - Better to extract partial data than skip the row

4. VERIFY BEFORE/AFTER CONTEXT:
   - Look at the row BEFORE and AFTER each item
   - Are there gaps in the table? → You missed a row
   - Is there extra vertical space? → Hidden row there

5. DOUBLE COUNT:
   - Count rows at START of extraction
   - Count items in your JSON at END
   - Numbers MUST match - if not, you skipped rows

STEP 2: EXTRACT EACH ROW CAREFULLY

For each row in the table:
1. Find the item name/description (usually longest text field)
2. Find the rate (price per unit) - look for "Rate" column or "x.xx x" notation
3. Find the quantity - look for "Qty" column or "x y.yy" notation
4. Find the amount (total) - usually the last/rightmost number
5. Verify: amount should equal rate × quantity (allow small rounding differences)

STEP 3: HANDLE DIFFERENT FORMATS

Format A: "Rate x Qty" notation
```
DENGUE IGM AND IGG    640.00 x 1.00    640.00
```
Extract: rate=640.00, qty=1.00, amount=640.00

Format B: Separate columns
```
Item Name              | Rate   | Qty  | Amount
Consultation           | 350.00 | 2.00 | 700.00
```
Extract: rate=350.00, qty=2.00, amount=700.00

Format C: Only amount visible
```
BED CHARGE GENERAL WARD    1500.00
```
Extract: rate=1500.00, qty=1.00, amount=1500.00

Format D: ⚠️ **PHARMACY BILLS - Quantity PREFIX in Item Name** ⚠️
```
3 x Igurat 25          Batch: 948    Rs: 942.00
20 caps Brilamox       Batch: 821    Rs: 238.00
5 tabs Paracetamol     Batch: 123    Rs: 50.00
```

🔥 CRITICAL PHARMACY EXTRACTION RULES:

1. **DETECT QUANTITY PREFIX PATTERNS:**
   Look for these patterns at the START of item names:
   - "3 x Medicine" → qty=3, name="Medicine"
   - "20 caps Medicine" → qty=20, name="Medicine"
   - "5 tabs Medicine" → qty=5, name="Medicine"
   - "10 tab Medicine" → qty=10, name="Medicine"
   - "2x Medicine" → qty=2, name="Medicine" (no space)
   - "15 units Medicine" → qty=15, name="Medicine"

2. **EXTRACTION STEPS:**
   Step 1: Read the full item name text
   Step 2: Check if it starts with a NUMBER followed by:
           - "x" or "X"
           - "caps" or "cap"
           - "tabs" or "tab"
           - "units" or "unit"
   Step 3: If pattern found:
           - Extract the NUMBER as item_quantity
           - Remove the quantity prefix to get clean item_name
           - Calculate item_rate = item_amount ÷ item_quantity
   Step 4: If NO pattern found:
           - Look for separate Qty column
           - If no Qty column, default to qty=1.0

3. **EXAMPLES:**

   Example 1:
   ```
   Text: "3 x Igurat 25"
   Amount: 942.00
   ```
   ✅ CORRECT Extraction:
   - item_name: "Igurat 25"
   - item_quantity: 3.0
   - item_amount: 942.0
   - item_rate: 942.0 ÷ 3.0 = 314.0

   ❌ WRONG:
   - item_name: "3 x Igurat 25" (includes quantity prefix)
   - item_quantity: 1.0 (missed the "3 x")

   Example 2:
   ```
   Text: "20 caps Brilamox"
   Amount: 238.00
   ```
   ✅ CORRECT Extraction:
   - item_name: "Brilamox"
   - item_quantity: 20.0
   - item_amount: 238.0
   - item_rate: 238.0 ÷ 20.0 = 11.9

   ❌ WRONG:
   - item_name: "20 caps Brilamox" (includes quantity prefix)
   - item_quantity: 1.0 (missed the "20 caps")

   Example 3:
   ```
   Text: "5 tabs Paracetamol 500mg"
   Amount: 50.00
   ```
   ✅ CORRECT Extraction:
   - item_name: "Paracetamol 500mg"
   - item_quantity: 5.0
   - item_amount: 50.0
   - item_rate: 50.0 ÷ 5.0 = 10.0

4. **RATE CALCULATION RULE:**
   - When quantity is in item name: item_rate = item_amount ÷ item_quantity
   - When quantity is in column: Use the rate from Rate column
   - ALWAYS verify: item_amount ≈ item_rate × item_quantity (allow 5% rounding)

5. **CLEAN ITEM NAME:**
   After extracting quantity, remove these prefixes:
   - "3 x " → remove
   - "20 caps " → remove
   - "5 tabs " → remove
   - "10 tab " → remove
   - "2x " → remove (no space)

   Keep only the medicine/product name

⛔ WHAT NOT TO DO - COMMON MISTAKES TO AVOID:

MISTAKE #1: Mixing up Rate and Quantity
❌ WRONG:
```
Item: PHARMACY CHARGE
Rate: 70491.00, Qty: 0.75, Amount: 52868.25
```
✅ CORRECT:
```
Item: PHARMACY CHARGE
Rate: 70491.00, Qty: 0.75, Amount: 52868.25
(This is correct - verify: 70491 × 0.75 = 52868.25 ✓)
```

MISTAKE #2: Taking values from wrong row
❌ WRONG: Taking the amount from next row
❌ WRONG: Taking the rate from previous row
✅ CORRECT: All values (rate, qty, amount) come from the SAME row

MISTAKE #3: Merging identical items
❌ WRONG:
```
Consultation appears 4 times → Extract only 1 item
```
✅ CORRECT:
```
Consultation appears 4 times → Extract 4 SEPARATE items
```

MISTAKE #4: Wrong column alignment
❌ WRONG:
```
Row: "Consultation for Inpatients  350.00 x 1.00  350.00"
Extracted: qty=2.00 (from different row!)
```
✅ CORRECT:
```
Row: "Consultation for Inpatients  350.00 x 1.00  350.00"
Extracted: rate=350.00, qty=1.00, amount=350.00
```

MISTAKE #5: Extracting subtotals as items
❌ WRONG: Extract "Total of BED CHARGES: 6000.00" as an item
✅ CORRECT: Skip subtotals, only extract actual line items

MISTAKE #6: Skipping items with same name
❌ WRONG: "BED CHARGE" appears 4 times → extract only 1
✅ CORRECT: "BED CHARGE" appears 4 times → extract ALL 4

MISTAKE #7: Extracting discount/total rows as items
❌ WRONG:
```
Extract: "GST DISCOUNT" with amount -500.00 as a line item
Extract: "Total" with amount 5000.00 as a line item
```
✅ CORRECT:
```
Skip: "GST DISCOUNT" (this is a discount, not a billable item)
Skip: "Total" (this is a summary row, not a billable item)
Skip: "Cash Discount" (discount row)
Skip: "Sub Total" (summary row)
Only extract actual billable items/services/products
```

HOW TO IDENTIFY DISCOUNT/TOTAL ROWS:
- Row name contains: "DISCOUNT", "TOTAL", "TAX", "GST", "CGST", "SGST"
- Row has negative amount (e.g., -500.00, -1000.00)
- Row appears after all items at bottom of invoice
- Row is in a different format (bold, larger font, separate section)

EXTRACTION RULES:

1. EXTRACT EVERY ROW:
   - Each row in the main invoice table = 1 item in your output
   - If you see 50 rows, return 50 items
   - DO NOT skip, merge, or summarize

2. MATCH COLUMNS CORRECTLY:
   - For each row, take rate/qty/amount from THAT row only
   - Do NOT mix values from different rows
   - Follow the column structure of the table

3. HANDLE REPEATED ITEMS:
   - Same name, same values (all fields identical) → Still extract EACH occurrence
   - Same name, different values → Definitely extract each as separate item

4. CRITICAL: ONE IMAGE = ONE PAGE OBJECT

   IMPORTANT: You are processing IMAGES of invoice pages. Each IMAGE you see is ONE page in the document.

   **If one image contains multiple invoice slips/receipts:**
   - Extract ALL items from ALL slips on that image
   - Put them ALL into ONE page object
   - Use the same page_no for all items from that image
   - Do NOT create separate page objects for each slip

   Example:
   - Image shows 2 yellow invoice slips side by side
   - Extract all items from BOTH slips
   - Put them in ONE page object (e.g., page_no: "3")
   - Result: One page_no with all items from both slips ✓

   DO NOT:
   - Create page_no "3" for first slip and page_no "4" for second slip ❌
   - Split items from the same image into different page objects ❌

5. PAGE CLASSIFICATION (MUST ALWAYS BE SET - NEVER NULL):

   You MUST classify each page as one of these three types:

   A) "Bill Detail" - Pages with CATEGORIZED sections and sub-details
      Characteristics:
      - Has section headers (ROOM CHARGES, CONSULTATION CHARGES, LABORATORY CHARGES, etc.)
      - Shows "SubTotal:" for each category/section
      - Items are grouped under category headers
      - May have nested structure (category → items → subtotal)
      - Usually the main detailed breakdown pages
      Example:
      ```
      ROOM CHARGES                    SubTotal: ₹4500
        ICU ROOM RENT CHARGES  ...
      ADMISSION CHARGES               SubTotal: ₹100.00
        IP REGISTRATION FEES   ...
      LABORATORY CHARGES              SubTotal: ₹23030.00
        PUS CULTURE & SENSITIVITY ...
        Complete Blood Count ...
      ```

   B) "Final Bill" - Summary/consolidated page with final totals
      Characteristics:
      - Usually titled "FINAL BILL", "DETAIL FINAL BILL", "BILL SUMMARY"
      - Shows department-wise totals ("Total of PATHOLOGY:", "Total of PHARMACY CHARGE:")
      - Has "Grand Total:", "Net Total:", "Final Amount:"
      - Consolidates charges from multiple departments
      - May show overall summary of the entire invoice
      Example:
      ```
      DETAIL FINAL BILL
      Laboratory tests...
      Total of PATHOLOGY: 10098.00
      PHARMACY CHARGE
      Total of PHARMACY CHARGE: 52868.25
      Grand Total: 73420.25
      ```

   C) "Pharmacy" - Simple list of pharmacy/medicine items WITHOUT complex categorization
      Characteristics:
      - Plain list of medicines/pharmacy items
      - NO category headers or subtotals between items
      - Just item name, batch, quantity, rate, amount
      - No nested structure - flat list
      - Typically shows: Medicine name | Batch | Exp | Qty | Rate | Amount
      Example:
      ```
      Telma 20mg        BATCH123  1  100.00  100.00
      Okamel-500        BATCH456  2  50.00   100.00
      Paracetamol 500mg BATCH789  3  10.00   30.00
      ```

   CRITICAL RULES FOR PAGE TYPE:
   - EVERY page MUST have a page_type - NEVER leave it null or empty
   - If unclear, default to "Bill Detail"
   - Look for these indicators:
     * Section headers with "SubTotal" → "Bill Detail"
     * "Grand Total", "Final Bill" in title → "Final Bill"
     * Flat medicine list without sections → "Pharmacy"
   - Same invoice can have multiple page types across different pages

5. SKIP THESE (NOT line items):
   - Subtotals ("Total of X: ...", "Sub Total: ...")
   - Grand totals ("Grand Total: ...", "Total: ...", "Net Total: ...")
   - Tax totals ("Tax: ...", "GST: ...", "CGST: ...", "SGST: ...")
   - DISCOUNT rows ("GST DISCOUNT", "DISCOUNT", "Cash Discount", "Special Discount", etc.)
   - Any row with negative amounts (these are usually discounts/refunds)
   - Section headers (rows that group items but have no quantity/amount themselves)
   - Summary rows
   - **GROUP HEADER ROWS**: Rows that:
     * Have a service/item name with code (e.g., "Consultation (999311)")
     * But NO quantity, rate, or amount in the rightmost columns
     * Are followed by indented sub-items with actual data
     * Act as category headers for items below them
     * Example: Skip "Consultation (999311)" if followed by "OP Consultation - Follow Up Visit" with actual values

6. FIELD FORMATTING:
   - Remove currency symbols (₹, $)
   - Remove commas from numbers (1,000 → 1000)
   - Keep as decimal numbers (100 → 100.0)

VALIDATION CHECKS (Do these before responding):

✓ Check 1: COUNT ROWS CAREFULLY
   - Look at the invoice image
   - Count EVERY horizontal row in the table (even faint ones)
   - Count items in your JSON
   - They MUST be equal
   - If not equal, you MISSED rows - go back and find them

✓ Check 2: CHECK FOR GAPS
   - Look for unusual vertical spacing between rows
   - Large gap = likely a missed row with faint text
   - Check row numbers (if present) for missing numbers
   - Scan the entire table area line by line

✓ Check 3: VERIFY AMOUNTS
   - For each item, verify amount ≈ rate × quantity
   - Allow 1% difference for rounding
   - If calculation is off, you may have wrong column values

✓ Check 4: NO SUBTOTALS
   - Ensure no "Total", "Subtotal", "Grand Total" in items
   - Only extract actual billable line items

✓ Check 5: ALL REPEATED ITEMS EXTRACTED
   - Items with same name should all be extracted
   - Don't merge or skip duplicates

✓ Check 6: COLUMN ALIGNMENT
   - Verify rate from rate column, qty from qty column
   - No mixing of column values

✓ Check 7: NO DISCOUNT/TOTAL/HEADER ROWS
   - Check each extracted item name
   - If name contains "DISCOUNT", "TOTAL", "TAX", "GST" → Remove it
   - If amount is negative → Likely a discount, remove it
   - If row has service name with code like "(999311)" but NO actual quantity/amount data → It's a header, remove it
   - Only extract rows that have COMPLETE data: name + quantity + rate + amount
   - Skip group headers that categorize items below them
   - Only actual billable products/services with full data should remain

✓ Check 8: PAGE TYPE IS ALWAYS SET
   - EVERY page MUST have a page_type value
   - Check each page in your JSON
   - If page_type is null, empty, or missing → Set to "Bill Detail"
   - Valid values ONLY: "Bill Detail", "Final Bill", "Pharmacy"
   - Look at page characteristics to choose correct type:
     * Has section headers + SubTotals → "Bill Detail"
     * Has Grand Total + department totals → "Final Bill"
     * Flat list of medicines → "Pharmacy"

✓ Check 9: PHARMACY QUANTITY PREFIX HANDLING
   - Look for item names starting with patterns: "3 x", "20 caps", "5 tabs", etc.
   - If found, verify:
     * item_quantity = the number from prefix (e.g., "3 x" → qty=3.0)
     * item_name = medicine name WITHOUT the quantity prefix
     * item_rate = item_amount ÷ item_quantity
   - Examples to verify:
     * "3 x Igurat 25" with amount 942 → qty=3.0, name="Igurat 25", rate=314.0 ✓
     * "20 caps Brilamox" with amount 238 → qty=20.0, name="Brilamox", rate=11.9 ✓
   - If you see quantity in item name but qty=1.0 → WRONG, fix it!

⚠️ CRITICAL: If you're extracting from a POOR QUALITY scan:
- Expect to work harder to find all rows
- Some text will be faint - that's OK, extract what you can
- ROW COUNT is your primary verification tool
- Better to extract 22/22 rows with some uncertain text than to extract only 18/22 rows perfectly

EXAMPLE 1 - CORRECT EXTRACTION:

Invoice shows:
```
S.No | Item Name              | Rate    | Qty  | Amount
1.   | Consultation           | 350.00  | 2.00 | 700.00
2.   | Consultation           | 350.00  | 2.00 | 700.00
3.   | Consultation           | 350.00  | 1.00 | 350.00
4.   | BED CHARGE            | 1500.00 | 1.00 | 1500.00
     | Sub Total              |         |      | 3750.00
     | GST DISCOUNT           |         |      | -500.00
     | Total                  |         |      | 3250.00
```

CORRECT JSON:
```json
{
  "bill_items": [
    {"item_name": "Consultation", "item_rate": 350.0, "item_quantity": 2.0, "item_amount": 700.0},
    {"item_name": "Consultation", "item_rate": 350.0, "item_quantity": 2.0, "item_amount": 700.0},
    {"item_name": "Consultation", "item_rate": 350.0, "item_quantity": 1.0, "item_amount": 350.0},
    {"item_name": "BED CHARGE", "item_rate": 1500.0, "item_quantity": 1.0, "item_amount": 1500.0}
  ]
}
```

Note: 4 ACTUAL items in table → 4 items in JSON ✓
Note: "Sub Total", "GST DISCOUNT", "Total" are NOT included (correctly skipped) ✓
Note: Item #3 has qty=1.0 (not 2.0) - read from correct row ✓

EXAMPLE 2 - SKIPPING GROUP HEADERS:

Invoice shows:
```
S.No | Service Type/Service Name           | Department   | Qty | Ref Tariff | Amount (INR)
1    | Consultation (999311)               |              |     |            |
  1  | OP Consultation - Follow Up Visit   | Consultation | 1   | 2,000.00   | 2,000.00
```

❌ WRONG - Extracting the header:
```json
{
  "bill_items": [
    {"item_name": "Consultation (999311)", "item_rate": 2000.0, "item_quantity": 1.0, "item_amount": 2000.0},
    {"item_name": "OP Consultation - Follow Up Visit", "item_rate": 2000.0, "item_quantity": 1.0, "item_amount": 2000.0}
  ]
}
```

✅ CORRECT - Skipping the header, extracting only the actual item:
```json
{
  "bill_items": [
    {"item_name": "OP Consultation - Follow Up Visit", "item_rate": 2000.0, "item_quantity": 1.0, "item_amount": 2000.0}
  ]
}
```

Why skip "Consultation (999311)"?
- It's a GROUP HEADER that categorizes items below it
- The row has NO quantity (empty cell)
- The row has NO amount in the rightmost column for that row
- The actual billable item is "OP Consultation - Follow Up Visit" which IS indented/sub-item
- Only extract rows with COMPLETE data: name + quantity + rate + amount

EXAMPLE - PAGE TYPE CLASSIFICATION:

Page 1 shows:
```
ROOM CHARGES                    SubTotal: ₹4500
  ICU ROOM RENT CHARGES  3  ₹15000.00  ₹45000.00
ADMISSION CHARGES               SubTotal: ₹100.00
  IP REGISTRATION FEES   1  ₹100.00    ₹100.00
LABORATORY CHARGES              SubTotal: ₹23030.00
  Complete Blood Count   1  ₹450.00    ₹450.00
```
→ page_type: "Bill Detail" (has section headers and SubTotals)

Page 2 shows:
```
DETAIL FINAL BILL
Laboratory tests...
Total of PATHOLOGY: 10098.00
PHARMACY CHARGE
Total of PHARMACY CHARGE: 52868.25
Grand Total: 73420.25
```
→ page_type: "Final Bill" (shows grand total and department totals)

Page 3 shows:
```
Telma 20mg        BATCH123  1  100.00  100.00
Okamel-500        BATCH456  2   50.00  100.00
Paracetamol 500mg BATCH789  3   10.00   30.00
```
→ page_type: "Pharmacy" (flat list of medicines, no sections)

EXAMPLE - PHARMACY BILL WITH QUANTITY PREFIX:

Invoice shows (handwritten pharmacy bill):
```
┌─────┬──────────────────────────┬─────────┬─────────┬───────┬────────┬──────┐
│ Qty │ Name of the Drugs        │ Batch No│ Exp.Date│ Mfg.  │ Rs.    │ P.   │
├─────┼──────────────────────────┼─────────┼─────────┼───────┼────────┼──────┤
│ 3xJp.l │ J Gujarat 25          │ 948     │ 10/26   │ 24    │ 942.00 │      │
│ 20ufabs │ Brilamox             │ 821     │ 8/26    │ 3h5   │ 238.00 │      │
│     │                          │         │         │       │        │      │
│     │                          │         │         │ Total │1180.00 │      │
└─────┴──────────────────────────┴─────────┴─────────┴───────┴────────┴──────┘
Date: 24/9/25
```

Reading the Qty column:
- Row 1: "3xJp.l" → This is "3 x [something]" (quantity prefix format)
- Row 2: "20ufabs" → This is "20 [caps/tabs]" (quantity prefix format)

Reading the Name column:
- Row 1: "J Gujarat 25" → This is the medicine name (likely "Igurat 25")
- Row 2: "Brilamox" → This is the medicine name

✅ CORRECT Extraction:
```json
{
  "pagewise_line_items": [
    {
      "page_no": "1",
      "page_type": "Pharmacy",
      "bill_items": [
        {
          "item_name": "Igurat 25",
          "item_quantity": 3.0,
          "item_amount": 942.0,
          "item_rate": 314.0
        },
        {
          "item_name": "Brilamox",
          "item_quantity": 20.0,
          "item_amount": 238.0,
          "item_rate": 11.9
        }
      ]
    }
  ]
}
```

Explanation:
- Row 1: "3xJp.l J Gujarat 25" → Combined text is "3 x Igurat 25"
  * Detected pattern: "3 x" at start
  * Extracted quantity: 3.0
  * Cleaned name: "Igurat 25"
  * Calculated rate: 942.0 ÷ 3.0 = 314.0
- Row 2: "20ufabs Brilamox" → Combined text is "20 caps Brilamox" or similar
  * Detected pattern: "20 caps" at start
  * Extracted quantity: 20.0
  * Cleaned name: "Brilamox"
  * Calculated rate: 238.0 ÷ 20.0 = 11.9
- Skipped "Total 1180.00" row (summary row, not an item)

❌ WRONG Extraction:
```json
{
  "bill_items": [
    {
      "item_name": "3xJp.l J Gujarat 25",  ❌ Should not include quantity prefix
      "item_quantity": 1.0,                 ❌ Should be 3.0
      "item_amount": 942.0,
      "item_rate": 942.0                    ❌ Should be 314.0
    }
  ]
}
```

EXAMPLE - POOR QUALITY SCAN WITH MISSING ROWS:

❌ WRONG APPROACH:
```
You see rows: 1, 2, 3, (faint row - skip it), 5, 6
You extract: 5 items
Result: MISSED 1 ROW ❌
```

✅ CORRECT APPROACH:
```
You see rows: 1, 2, 3, (faint row - can barely read "ITEM_NAME"), 5, 6
Count: 6 rows total (including faint one)
You extract: 6 items (even if row 4 has uncertain text)
Result: ALL ROWS EXTRACTED ✓

For faint row #4:
- If you can read partial text: Use that
- If totally unreadable: Use "Unknown Item" or "Item 4"
- Still extract the rate/qty/amount if visible
- Don't skip the row!
```

DETECTION STRATEGY FOR MISSING ROWS:

1. VISUAL SCAN:
   - Scan top to bottom of invoice table
   - Look for ALL horizontal separators/lines
   - Each line = potential row

2. SPACING CHECK:
   - Normal spacing between rows: Small gap
   - Large gap between rows: Likely missed a faint row there
   - Check those gaps carefully

3. SEQUENTIAL CHECK:
   - If S.No exists: 1, 2, 3, ?, 5, 6 → Row 4 missing!
   - If amounts: 100, 200, 300, (gap), 500 → Check the gap
   - Look for patterns and breaks

4. FINAL COUNT:
   - Before responding, count rows one more time
   - Verify your JSON has same number of items
   - If mismatch, find the missing rows

FINAL REMINDER:
- **ONE IMAGE = ONE PAGE OBJECT**: If an image has 2 invoice slips, extract ALL items into ONE page object
- Extract EVERY billable item row as a SEPARATE item
- DO NOT extract discount rows (GST DISCOUNT, Cash Discount, etc.)
- DO NOT extract total/subtotal rows (Total, Sub Total, Grand Total, etc.)
- DO NOT extract tax summary rows (GST, CGST, SGST when shown as totals)
- DO NOT extract group header rows (rows with service codes but no quantity/amount)
- Match columns CORRECTLY (don't mix up rate/qty/amount)
- COUNT ROWS and verify you didn't miss any ACTUAL billable items
- ALWAYS SET page_type for EVERY page (NEVER null/empty)
  * Section headers + SubTotals = "Bill Detail"
  * Grand Total + Final Bill title = "Final Bill"
  * Flat medicine list = "Pharmacy"
- For poor scans, work extra hard to find ALL rows
- Better to have partial data than missing rows
- Verify your extraction before responding
- Return ONLY valid JSON (no markdown, no code blocks)

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
                            "description": "Type of page - REQUIRED, NEVER NULL. Must be one of: 'Bill Detail' (pages with section headers and SubTotals), 'Final Bill' (summary page with Grand Total and department totals), or 'Pharmacy' (flat list of medicines without sections). Analyze page structure to choose correct type."
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
