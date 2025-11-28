# Invoice OCR System

A robust, production-ready FastAPI-based invoice OCR system that extracts structured data from PDF and image invoices using LLM-based processing with advanced error handling and retry mechanisms.

## Features

### Core Capabilities
- **Multi-Page Processing**: Handles PDF and image files (JPEG, PNG, HEIC)
- **Pagewise Line Item Extraction**: Extracts line items and tracks which page each item appears on
- **Multi-Provider Support**: Works with Google Gemini, OpenAI, or local Ollama models
- **Structured Output**: Returns standardized JSON with pagewise line items and token usage

### Robustness & Reliability
- **Advanced JSON Repair**: 7 different JSON repair strategies to handle malformed LLM responses
- **Intelligent Chunking**: Processes large documents in chunks to avoid truncation errors
- **Data Validation**: Comprehensive validation and cleaning of extracted data
- **Duplicate Removal**: Automatically detects and removes duplicate line items
- **Large Document Support**: Handles 50+ page invoices by splitting into manageable chunks
- **Error Recovery**: Graceful degradation with informative error messages
- **Truncation Handling**: Salvages partial data from incomplete responses

### Extensibility
- **Modular Architecture**: Clean separation of concerns with utility modules
- **Configurable**: Environment-based configuration for easy deployment
- **Provider-Agnostic**: Easy to add new LLM providers
- **Comprehensive Logging**: Detailed logging for debugging and monitoring

## Installation

### Prerequisites

- Python 3.8+
- Poppler (for PDF processing)

Install Poppler on macOS:
```bash
brew install poppler
```

### Setup

1. Clone or navigate to the project directory:
```bash
cd /Users/likhithbhargav/Desktop/ocr
```

2. Create and activate virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create `.env` file with your configuration:
```bash
# LLM Configuration
LLM_PROVIDER=gemini  # Options: "gemini", "openai", "ollama"
GEMINI_API_KEY=your_gemini_api_key_here
# OPENAI_API_KEY=your_openai_api_key_here

# Model Configuration
GEMINI_MODEL=gemini-2.0-flash  # Recommended for best results
# OPENAI_MODEL=gpt-4o-mini

# Ollama Configuration (for local models)
# OLLAMA_BASE_URL=http://localhost:11434
# OLLAMA_MODEL=llava

# Processing Limits
MAX_PAGES_PER_INVOICE=50
MAX_FILE_SIZE_MB=10
PAGES_PER_CHUNK=3  # Process large docs in chunks to avoid truncation

# LLM Settings
LLM_TEMPERATURE=0.1
LLM_TIMEOUT=60
MAX_OUTPUT_TOKENS=8192  # Maximum tokens for LLM response

# Logging
LOG_LEVEL=INFO
```

## How It Works - Intelligent Chunking

For large invoices (more than 3 pages), the system automatically processes them in chunks to avoid LLM response truncation:

### Example: 6-Page Invoice

1. **Chunk 1** (Pages 1-3):
   - Send to LLM → Extract items → Success
   - Token usage: ~3,500 tokens

2. **Chunk 2** (Pages 4-6):
   - Send to LLM → Extract items → Success
   - Token usage: ~3,500 tokens

3. **Combine Results**:
   - Merge all pagewise_line_items
   - Total token usage: ~7,000 tokens
   - Return complete response

### Why Chunking?

**Problem**: Large invoices with many items cause LLM responses to be truncated
**Solution**: Process in smaller chunks, each within token limits
**Benefit**: 100% data extraction, no truncation errors

### Tuning Chunk Size

Adjust `PAGES_PER_CHUNK` based on your invoice density:

- **Sparse invoices** (few items per page): `PAGES_PER_CHUNK=5`
- **Normal invoices** (moderate items): `PAGES_PER_CHUNK=3` (default)
- **Dense invoices** (many items per page): `PAGES_PER_CHUNK=2`

```bash
# In .env
PAGES_PER_CHUNK=3  # Adjust based on your needs
```

## Usage

### Start the Server

```bash
source venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at: `http://localhost:8000`

### API Documentation

Interactive API documentation (Swagger UI): `http://localhost:8000/docs`

### API Endpoints

#### Extract Bill Data (Submission Format)

**Endpoint**: `POST /extract-bill-data`

This is the official submission endpoint that matches the required API signature.

**Request**:
```json
{
  "document": "https://hackrx.blob.core.windows.net/assets/datathon-IIT/sample_2.png"
}
```

**Response**:
```json
{
  "is_success": true,
  "token_usage": {
    "total_tokens": 10169,
    "input_tokens": 2074,
    "output_tokens": 8095
  },
  "data": {
    "pagewise_line_items": [
      {
        "page_no": "1",
        "page_type": "Bill Detail",
        "bill_items": [
          {
            "item_name": "REGISTRATION",
            "item_quantity": 1.0,
            "item_rate": 100.0,
            "item_amount": 100.0
          },
          {
            "item_name": "CONSULTATION",
            "item_quantity": 1.0,
            "item_rate": 500.0,
            "item_amount": 500.0
          }
        ]
      }
    ],
    "total_item_count": 2
  }
}
```

#### Process Invoice from URL (Alternative)

**Endpoint**: `POST /api/v1/invoices/process`

Same functionality as `/extract-bill-data` with identical request/response format.

#### Upload Invoice File

**Endpoint**: `POST /api/v1/invoices/upload`

Upload a file directly instead of providing a URL.

**Request**: Multipart form data with file upload

**Response**: Same as `/extract-bill-data`

#### Health Check

**Endpoint**: `GET /api/v1/health`

**Response**:
```json
{
  "status": "healthy"
}
```

## Project Structure

```
ocr/
├── main.py                         # FastAPI application
├── config/
│   └── config.py                  # Configuration management
├── models/
│   └── models.py                  # Pydantic data models
├── services/
│   ├── invoices_ocr_service.py    # Main OCR service
│   ├── invoices_ocr_prompts.py    # Prompt generation
│   └── llm_wrapper.py             # LLM provider wrapper
├── utils/                          # Utility modules (NEW)
│   ├── json_repair.py             # JSON parsing & repair utilities
│   ├── retry.py                   # Retry logic with exponential backoff
│   └── data_validator.py          # Data validation & cleaning
├── static/                         # Frontend files
│   └── index.html                 # Web interface
├── requirements.txt               # Python dependencies
├── .env                           # Environment variables
└── README.md                      # This file
```

## Configuration

### Environment Variables

- `LLM_PROVIDER`: LLM provider to use (`gemini` or `openai`)
- `GEMINI_API_KEY`: Google Gemini API key
- `OPENAI_API_KEY`: OpenAI API key
- `GEMINI_MODEL`: Gemini model name (default: `gemini-1.5-flash`)
- `OPENAI_MODEL`: OpenAI model name (default: `gpt-4o-mini`)
- `MAX_PAGES_PER_INVOICE`: Maximum pages to process (default: 50)
- `MAX_FILE_SIZE_MB`: Maximum file size in MB (default: 10)

## Example Usage

### Using cURL

```bash
curl -X POST "http://localhost:8000/api/v1/invoices/process" \
  -H "Content-Type: application/json" \
  -d '{"document": "https://example.com/invoice.pdf"}'
```

### Using Python

```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/invoices/process",
    json={"document": "https://example.com/invoice.pdf"}
)

data = response.json()
if data["is_success"]:
    print(f"Total items: {data['data']['total_item_count']}")
    print(f"Reconciled amount: {data['data']['reconciled_amount']}")
```

## Troubleshooting

### Common Issues and Solutions

#### 1. "Unterminated string starting at: line X column Y (char Z)"

**Problem**: The LLM generated malformed JSON with unterminated strings.

**Solution**: This is now automatically handled by the new JSON repair utilities. The system will:
- Try 7 different repair strategies
- Automatically retry with exponential backoff (up to 3 times)
- Clean and validate the JSON before returning

If you still encounter this error, check the logs for more details:
```bash
tail -f app.log
```

#### 2. Empty Results (`pagewise_line_items: []`)

**Problem**: The LLM returned no extracted data even though the invoice has items.

**Solutions**:
1. **Check your API key**: Ensure your Gemini/OpenAI API key is valid
2. **Verify the model**: Use `gemini-2.0-flash` for best results (set in `.env`)
3. **Check document quality**: Ensure the invoice image is clear and readable
4. **Review logs**: Check application logs for extraction warnings
5. **Try different provider**: If using Gemini, try OpenAI or vice versa

The improved prompts now explicitly instruct the LLM to extract all data and not return empty results.

#### 3. Large Invoices Timing Out

**Problem**: Processing large invoices (many pages) causes timeout errors.

**Solutions**:
1. The system now uses dynamic timeout scaling (30s per page, minimum 120s)
2. Adjust `MAX_PAGES_PER_INVOICE` in `.env` if needed:
   ```bash
   MAX_PAGES_PER_INVOICE=100  # Increase for larger documents
   ```
3. For very large invoices, consider splitting into smaller documents

#### 4. Poppler Not Found

If you get an error about Poppler not being found:
```bash
# macOS
brew install poppler

# Ubuntu/Debian
sudo apt-get install poppler-utils

# CentOS/RHEL
sudo yum install poppler-utils
```

#### 5. API Key Issues

Make sure your `.env` file contains the correct API key for your chosen LLM provider:
```bash
# Check your .env file
cat .env | grep API_KEY

# Verify the key is not empty
echo $GEMINI_API_KEY
```

#### 6. Memory Issues with Large PDFs

Adjust settings in `.env`:
```bash
MAX_PAGES_PER_INVOICE=50  # Reduce if needed
MAX_FILE_SIZE_MB=10       # Reduce if needed
```

#### 7. Debugging Issues

Enable detailed logging:
```bash
# In .env
LOG_LEVEL=DEBUG
```

Then restart the server and check logs:
```bash
# Watch logs in real-time
tail -f logs/app.log

# Or check uvicorn output
uvicorn main:app --reload --log-level debug
```

## System Architecture

### How It Works

1. **Document Processing**:
   - Download document from URL or accept file upload
   - Convert PDF pages to images (if needed)
   - Validate file size and page count

2. **LLM Processing** (with retry logic):
   - Send images to LLM with extraction prompt
   - LLM returns JSON with extracted data
   - Automatic retry (3 attempts) if extraction fails

3. **JSON Repair** (7 strategies):
   - Remove markdown code blocks
   - Extract JSON objects from text
   - Fix unterminated strings
   - Escape control characters
   - Validate structure
   - Use json5 parser as fallback

4. **Data Validation**:
   - Clean item names (remove control characters)
   - Validate numeric fields
   - Check calculation accuracy
   - Remove duplicates
   - Validate page types

5. **Response**:
   - Return structured JSON with token usage
   - Include error details if processing fails

### Extensibility

The system is designed to be easily extended:

1. **Adding New LLM Providers**:
   - Add new provider in `services/llm_wrapper.py`
   - Implement `_call_<provider>` method
   - Update `config.py` with provider settings

2. **Custom Validation Rules**:
   - Modify `utils/data_validator.py`
   - Add custom validation functions
   - Update validation logic in service

3. **Enhanced Prompts**:
   - Edit `services/invoices_ocr_prompts.py`
   - Add invoice-type specific prompts
   - Customize extraction rules

## Performance

- **Small invoices** (1-2 pages): ~10-15 seconds
- **Medium invoices** (5-10 pages): ~30-60 seconds
- **Large invoices** (20+ pages): ~2-3 minutes

Performance varies based on:
- LLM provider and model
- Document quality and complexity
- Network latency
- Number of line items

## Best Practices

1. **Use Gemini 2.0 Flash** for best balance of speed and accuracy
2. **Enable retry logic** (automatically enabled)
3. **Monitor logs** for extraction issues
4. **Validate critical data** in your application
5. **Use appropriate timeouts** for your use case
6. **Test with sample invoices** before production deployment

## License

MIT
