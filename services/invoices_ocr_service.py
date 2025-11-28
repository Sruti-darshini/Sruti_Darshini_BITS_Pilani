"""
Main Invoice OCR Service
"""
import os
import tempfile
from pathlib import Path
from typing import List, Dict, Any
import httpx
from pdf2image import convert_from_path
from PIL import Image, ImageEnhance, ImageFilter
import pillow_heif

from config.config import settings
from services.llm_wrapper import LLMWrapper
from services.invoices_ocr_prompts import generate_extraction_prompt, get_json_schema
from models.models import InvoiceData, PagewiseLineItems, BillItem, TokenUsage
from utils.data_validator import validate_and_clean_invoice_data, remove_duplicate_items
import logging

logger = logging.getLogger(__name__)

# Register HEIF opener for HEIC support
pillow_heif.register_heif_opener()


class InvoicesOCRService:
    """Service for processing invoices and extracting structured data"""
    
    def __init__(self):
        self.llm_wrapper = LLMWrapper()
        self.max_pages = settings.max_pages_per_invoice
        self.temp_dir = tempfile.mkdtemp()
    
    async def process_document(self, document_url: str) -> tuple[InvoiceData, TokenUsage]:
        """
        Process invoice from document URL
        
        Args:
            document_url: URL to the document (image or PDF)
            
        Returns:
            Tuple of (InvoiceData with extracted information, TokenUsage)
        """
        # Download document
        document_path = await self._download_document(document_url)
        
        try:
            # Convert to images
            image_paths = self._convert_to_images(document_path)
            
            # Extract data with LLM
            extracted_data, token_usage = self._extract_data_with_llm(image_paths)
            
            # Calculate totals
            invoice_data = self._calculate_totals(extracted_data)
            
            return invoice_data, TokenUsage(**token_usage)
            
        finally:
            # Cleanup
            self._cleanup(document_path, image_paths if 'image_paths' in locals() else [])
    
    async def process_file(self, file_path: str) -> tuple[InvoiceData, TokenUsage]:
        """
        Process invoice from local file path
        
        Args:
            file_path: Path to the local file
            
        Returns:
            Tuple of (InvoiceData with extracted information, TokenUsage)
        """
        try:
            # Convert to images
            image_paths = self._convert_to_images(file_path)
            
            # Extract data with LLM
            extracted_data, token_usage = self._extract_data_with_llm(image_paths)
            
            # Calculate totals
            invoice_data = self._calculate_totals(extracted_data)
            
            return invoice_data, TokenUsage(**token_usage)
            
        finally:
            # Cleanup image files (but not the original file)
            self._cleanup("", image_paths if 'image_paths' in locals() else [])
    
    async def _download_document(self, url: str) -> str:
        """Download document from URL"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            
            # Determine file extension from content type or URL
            content_type = response.headers.get("content-type", "")
            if "pdf" in content_type.lower():
                ext = ".pdf"
            elif "image" in content_type.lower():
                # Try to get extension from URL
                ext = Path(url).suffix or ".jpg"
            else:
                ext = Path(url).suffix or ".pdf"
            
            # Save to temp file
            temp_path = os.path.join(self.temp_dir, f"document{ext}")
            with open(temp_path, "wb") as f:
                f.write(response.content)
            
            return temp_path
    
    def _convert_to_images(self, document_path: str) -> List[str]:
        """
        Convert document to images
        
        Args:
            document_path: Path to the document file
            
        Returns:
            List of image file paths
        """
        file_ext = Path(document_path).suffix.lower()
        
        if file_ext == ".pdf":
            return self._convert_pdf_to_images(document_path)
        else:
            return self._process_image_file(document_path)
    
    def _convert_pdf_to_images(self, pdf_path: str) -> List[str]:
        """Convert PDF to images with configurable quality"""
        logger.info(f"Converting PDF to images at {settings.pdf_dpi} DPI")

        # Convert PDF to images with higher DPI
        images = convert_from_path(
            pdf_path,
            dpi=settings.pdf_dpi,
            fmt="jpeg",
            thread_count=2
        )

        # Check page limit
        if len(images) > self.max_pages:
            raise ValueError(
                f"PDF has {len(images)} pages, exceeds limit of {self.max_pages}"
            )

        # Save images with enhancement
        image_paths = []
        for i, image in enumerate(images):
            # Enhance image if enabled
            if settings.enable_image_enhancement:
                image = self._enhance_image(image)

            image_path = os.path.join(self.temp_dir, f"page_{i+1}.jpg")
            image.save(image_path, "JPEG", quality=settings.image_quality)
            image_paths.append(image_path)
            logger.debug(f"Saved page {i+1} with quality={settings.image_quality}")

        return image_paths
    
    def _enhance_image(self, image: Image.Image) -> Image.Image:
        """
        Enhance image quality for better OCR

        Args:
            image: PIL Image object

        Returns:
            Enhanced PIL Image
        """
        try:
            # Convert to RGB if needed
            if image.mode != "RGB":
                image = image.convert("RGB")

            # Increase contrast (helps with faint text)
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.3)  # 1.3x contrast boost

            # Increase sharpness (helps with blurry scans)
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(1.5)  # 1.5x sharpness boost

            # Optional: Reduce noise (helps with grainy scans)
            # image = image.filter(ImageFilter.MedianFilter(size=3))

            logger.debug("Image enhancement applied")
            return image

        except Exception as e:
            logger.warning(f"Image enhancement failed: {e}, using original")
            return image

    def _process_image_file(self, image_path: str) -> List[str]:
        """Process single image file with enhancement"""
        # Open image
        image = Image.open(image_path)

        # Convert to RGB
        if image.mode != "RGB":
            image = image.convert("RGB")

        # Enhance if enabled
        if settings.enable_image_enhancement:
            image = self._enhance_image(image)

        # Save as high-quality JPEG
        output_path = os.path.join(self.temp_dir, "page_1.jpg")
        image.save(output_path, "JPEG", quality=settings.image_quality)
        logger.debug(f"Processed image with quality={settings.image_quality}")

        return [output_path]
    
    def _extract_data_with_llm(self, image_paths: List[str]) -> Dict[str, Any]:
        """Extract data using LLM"""
        prompt = generate_extraction_prompt()
        schema = get_json_schema()

        result = self.llm_wrapper.process_with_structured_output(
            image_paths=image_paths,
            prompt=prompt,
            json_schema=schema
        )

        # Log what the LLM extracted
        extracted_data, token_usage = result
        total_items = sum(len(page.get('bill_items', [])) for page in extracted_data.get('pagewise_line_items', []))
        logger.info(f"LLM extracted {total_items} items from {len(image_paths)} images before validation")

        return result
    
    def _calculate_totals(self, extracted_data: Dict[str, Any]) -> InvoiceData:
        """
        Calculate totals and create InvoiceData object

        Args:
            extracted_data: Raw data from LLM

        Returns:
            InvoiceData with calculated totals
        """
        # Validate and clean the data first
        logger.info("Validating and cleaning extracted data")
        validated_data = validate_and_clean_invoice_data(extracted_data)

        # IMPORTANT: DO NOT remove duplicates - invoices often have repeated line items
        # Each row in the invoice table is a separate billable item, even if identical
        # The LLM is instructed to extract EVERY row, including duplicates
        cleaned_data = validated_data  # Skip duplicate removal

        pagewise_items = []
        total_count = 0

        for page_data in cleaned_data.get("pagewise_line_items", []):
            bill_items = []

            for item_data in page_data.get("bill_items", []):
                try:
                    bill_item = BillItem(
                        item_name=item_data["item_name"],
                        item_amount=float(item_data["item_amount"]),
                        item_rate=float(item_data["item_rate"]),
                        item_quantity=float(item_data["item_quantity"])
                    )
                    bill_items.append(bill_item)
                    total_count += 1
                except Exception as e:
                    logger.warning(f"Failed to create BillItem from {item_data}: {e}")
                    continue

            # Get page_type from extracted data, ensure it's never null
            # Must be one of: "Bill Detail", "Final Bill", "Pharmacy"
            page_type = page_data.get("page_type", "Bill Detail")

            # If null, empty, or invalid, default to "Bill Detail"
            if not page_type or page_type not in ["Bill Detail", "Final Bill", "Pharmacy"]:
                page_type = "Bill Detail"

            if bill_items:  # Only add pages with items
                pagewise_items.append(PagewiseLineItems(
                    page_no=str(page_data["page_no"]),
                    page_type=page_type,
                    bill_items=bill_items
                ))

        logger.info(f"Extracted {total_count} items across {len(pagewise_items)} pages")

        return InvoiceData(
            pagewise_line_items=pagewise_items,
            total_item_count=total_count
        )
    
    def _cleanup(self, document_path: str, image_paths: List[str]):
        """Clean up temporary files"""
        try:
            if os.path.exists(document_path):
                os.remove(document_path)
            
            for image_path in image_paths:
                if os.path.exists(image_path):
                    os.remove(image_path)
        except Exception:
            pass  # Ignore cleanup errors
