"""
FastAPI Application for Invoice OCR
"""
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import logging
import os
import tempfile
from pathlib import Path

from models.models import DocumentRequest, OCRResponse, ErrorResponse
from services.invoices_ocr_service import InvoicesOCRService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Invoice OCR API",
    description="Extract structured data from invoice documents using LLM-powered OCR",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure as needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize OCR service
ocr_service = InvoicesOCRService()


@app.get("/")
async def root():
    """Serve the frontend HTML"""
    return FileResponse("static/index.html")


@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.post("/api/v1/invoices/process", response_model=OCRResponse)
async def process_invoice(request: DocumentRequest):
    """
    Process invoice from document URL
    
    Args:
        request: DocumentRequest with document URL
        
    Returns:
        OCRResponse with extracted invoice data
    """
    try:
        logger.info(f"Processing invoice from URL: {request.document}")
        
        # Process document
        invoice_data, token_usage = await ocr_service.process_document(request.document)
        
        logger.info(
            f"Successfully processed invoice: "
            f"{invoice_data.total_item_count} items"
        )
        
        return OCRResponse(
            is_success=True,
            token_usage=token_usage,
            data=invoice_data
        )
        
    except Exception as e:
        logger.error(f"Error processing invoice: {str(e)}", exc_info=True)
        
        # Return error response
        error_response = ErrorResponse(
            is_success=False,
            message=str(e)
        )
        
        return JSONResponse(
            status_code=500,
            content=error_response.model_dump()
        )


@app.post("/extract-bill-data", response_model=OCRResponse)
async def extract_bill_data(request: DocumentRequest):
    """
    Extract bill data from document URL (Submission Format Endpoint)
    
    Args:
        request: DocumentRequest with document URL
        
    Returns:
        OCRResponse with extracted invoice data and token usage
    """
    try:
        logger.info(f"Extracting bill data from URL: {request.document}")
        
        # Process document
        invoice_data, token_usage = await ocr_service.process_document(request.document)
        
        logger.info(
            f"Successfully extracted bill data: "
            f"{invoice_data.total_item_count} items, "
            f"tokens used: {token_usage.total_tokens}"
        )
        
        return OCRResponse(
            is_success=True,
            token_usage=token_usage,
            data=invoice_data
        )
        
    except Exception as e:
        logger.error(f"Error extracting bill data: {str(e)}", exc_info=True)
        
        # Return error response
        error_response = ErrorResponse(
            is_success=False,
            message=f"Failed to process document. {str(e)}"
        )
        
        return JSONResponse(
            status_code=500,
            content=error_response.model_dump()
        )


@app.post("/api/v1/invoices/upload", response_model=OCRResponse)
async def upload_invoice(file: UploadFile = File(...)):
    """
    Upload and process invoice file
    
    Args:
        file: Uploaded file (PDF or image)
        
    Returns:
        OCRResponse with extracted invoice data
    """
    try:
        logger.info(f"Processing uploaded file: {file.filename}")
        
        # Validate file type
        allowed_extensions = {'.pdf', '.jpg', '.jpeg', '.png', '.heic'}
        file_ext = Path(file.filename).suffix.lower()
        
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file_ext}. Allowed: {', '.join(allowed_extensions)}"
            )
        
        # Save uploaded file temporarily
        temp_dir = tempfile.mkdtemp()
        temp_path = os.path.join(temp_dir, file.filename)
        
        try:
            # Write file
            with open(temp_path, "wb") as f:
                content = await file.read()
                f.write(content)
            
            # Process the file directly
            invoice_data, token_usage = await ocr_service.process_file(temp_path)
            
            logger.info(
                f"Successfully processed file: "
                f"{invoice_data.total_item_count} items"
            )
            
            return OCRResponse(
                is_success=True,
                token_usage=token_usage,
                data=invoice_data
            )
            
        finally:
            # Cleanup
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                os.rmdir(temp_dir)
            except Exception:
                pass
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing uploaded file: {str(e)}", exc_info=True)
        
        error_response = ErrorResponse(
            is_success=False,
            message=str(e)
        )
        
        return JSONResponse(
            status_code=500,
            content=error_response.model_dump()
        )


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions"""
    error_response = ErrorResponse(
        is_success=False,
        message=exc.detail
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    
    error_response = ErrorResponse(
        is_success=False,
        message="Internal server error"
    )
    return JSONResponse(
        status_code=500,
        content=error_response.model_dump()
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
