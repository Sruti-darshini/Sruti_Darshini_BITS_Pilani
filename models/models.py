"""
Pydantic models for Invoice OCR API
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Literal


class DocumentRequest(BaseModel):
    """Request model for invoice processing"""
    document: str = Field(..., description="URL to the document (image or PDF)")


class BillItem(BaseModel):
    """Individual line item in the bill"""
    item_name: str = Field(..., description="Item description/name exactly as mentioned in the bill")
    item_amount: float = Field(..., description="Net amount of the item post discounts as mentioned in the bill")
    item_rate: float = Field(..., description="Unit price/rate exactly as mentioned in the bill")
    item_quantity: float = Field(..., description="Quantity exactly as mentioned in the bill")


class PagewiseLineItems(BaseModel):
    """Line items grouped by page"""
    page_no: str = Field(..., description="Page number as string")
    page_type: Literal["Bill Detail", "Final Bill", "Pharmacy"] = Field(
        ...,
        description="Type of page: Bill Detail, Final Bill, or Pharmacy"
    )
    bill_items: List[BillItem] = Field(default_factory=list, description="All items on this page")


class TokenUsage(BaseModel):
    """Token usage information from LLM calls"""
    total_tokens: int = Field(..., description="Cumulative tokens from all LLM calls")
    input_tokens: int = Field(..., description="Cumulative input tokens from all LLM calls")
    output_tokens: int = Field(..., description="Cumulative output tokens from all LLM calls")


class InvoiceData(BaseModel):
    """Complete invoice data"""
    pagewise_line_items: List[PagewiseLineItems] = Field(
        default_factory=list,
        description="Items grouped by page number"
    )
    total_item_count: int = Field(..., description="Count of items across all pages")


class OCRResponse(BaseModel):
    """Successful API response"""
    is_success: bool = Field(default=True, description="Success status - true if status code 200 and valid schema")
    token_usage: TokenUsage = Field(..., description="Token usage from LLM calls")
    data: InvoiceData = Field(..., description="Extracted invoice data")


class ErrorResponse(BaseModel):
    """Error API response"""
    is_success: bool = Field(default=False, description="Success status (always false for errors)")
    message: str = Field(..., description="Error message describing what went wrong")
