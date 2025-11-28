"""
LLM Wrapper for multiple providers (Gemini and OpenAI)
"""
import base64
import json
import logging
from typing import List, Dict, Any
from pathlib import Path

from config.config import settings
from utils.json_repair import repair_json, validate_invoice_structure, get_empty_invoice_structure
from utils.retry import RetryConfig, retry_with_config

logger = logging.getLogger(__name__)


class LLMWrapper:
    """Unified interface for multiple LLM providers"""
    
    def __init__(self):
        self.provider = settings.llm_provider
        self.temperature = settings.llm_temperature

        # Configure retry settings
        self.retry_config = RetryConfig(
            max_retries=3,
            initial_delay=2.0,
            max_delay=10.0,
            exponential_base=2.0
        )

        if self.provider == "gemini":
            import google.generativeai as genai
            genai.configure(api_key=settings.gemini_api_key)
            self.model_name = settings.gemini_model
            # Use the model name directly without GenerativeModel wrapper to avoid v1beta
            self.genai = genai
            self.client = None  # We'll call generate_content differently
        elif self.provider == "openai":
            from openai import OpenAI
            self.client = OpenAI(api_key=settings.openai_api_key)
            self.model_name = settings.openai_model
        elif self.provider == "ollama":
            # Ollama uses HTTP API, no special client needed
            self.base_url = settings.ollama_base_url
            self.model_name = settings.ollama_model
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")
    
    def process_with_structured_output(
        self,
        image_paths: List[str],
        prompt: str,
        json_schema: Dict[str, Any]
    ) -> tuple[Dict[str, Any], Dict[str, int]]:
        """
        Process images with LLM and return structured JSON output with token usage
        Uses chunking for large documents to avoid truncation

        Args:
            image_paths: List of paths to image files
            prompt: Text prompt for the LLM
            json_schema: JSON schema for structured output

        Returns:
            Tuple of (parsed JSON response, token usage dict)
        """
        # For large documents, process in chunks to avoid truncation
        max_images_per_batch = settings.pages_per_chunk

        if len(image_paths) > max_images_per_batch:
            logger.info(f"Processing {len(image_paths)} images in chunks of {max_images_per_batch}")
            return self._process_in_chunks(image_paths, prompt, json_schema, max_images_per_batch)

        # For small documents, process directly
        if self.provider == "gemini":
            return self._call_gemini(image_paths, prompt, json_schema)
        elif self.provider == "openai":
            return self._call_openai(image_paths, prompt, json_schema)
        elif self.provider == "ollama":
            return self._call_ollama(image_paths, prompt, json_schema)

    def _process_in_chunks(
        self,
        image_paths: List[str],
        prompt: str,
        json_schema: Dict[str, Any],
        chunk_size: int
    ) -> tuple[Dict[str, Any], Dict[str, int]]:
        """
        Process images in chunks and combine results

        Args:
            image_paths: List of all image paths
            prompt: Extraction prompt
            json_schema: JSON schema
            chunk_size: Number of images per chunk

        Returns:
            Combined results and total token usage
        """
        all_pagewise_items = []
        total_tokens = 0
        total_input_tokens = 0
        total_output_tokens = 0

        # Process in chunks
        for i in range(0, len(image_paths), chunk_size):
            chunk = image_paths[i:i + chunk_size]
            chunk_num = (i // chunk_size) + 1
            total_chunks = (len(image_paths) + chunk_size - 1) // chunk_size

            logger.info(f"Processing chunk {chunk_num}/{total_chunks} with {len(chunk)} images")

            try:
                if self.provider == "gemini":
                    result, token_usage = self._call_gemini(chunk, prompt, json_schema)
                elif self.provider == "openai":
                    result, token_usage = self._call_openai(chunk, prompt, json_schema)
                elif self.provider == "ollama":
                    result, token_usage = self._call_ollama(chunk, prompt, json_schema)

                # Accumulate results
                pagewise_items = result.get("pagewise_line_items", [])
                all_pagewise_items.extend(pagewise_items)

                # Accumulate token usage
                total_tokens += token_usage.get("total_tokens", 0)
                total_input_tokens += token_usage.get("input_tokens", 0)
                total_output_tokens += token_usage.get("output_tokens", 0)

                logger.info(f"Chunk {chunk_num} extracted {len(pagewise_items)} pages")

            except Exception as e:
                logger.error(f"Error processing chunk {chunk_num}: {str(e)}")
                # Continue with other chunks
                continue

        # Combine results
        combined_result = {
            "pagewise_line_items": all_pagewise_items
        }

        combined_token_usage = {
            "total_tokens": total_tokens,
            "input_tokens": total_input_tokens,
            "output_tokens": total_output_tokens
        }

        logger.info(f"Combined results: {len(all_pagewise_items)} pages, {total_tokens} total tokens")

        return combined_result, combined_token_usage
    
    def _call_gemini(
        self,
        image_paths: List[str],
        prompt: str,
        json_schema: Dict[str, Any]
    ) -> tuple[Dict[str, Any], Dict[str, int]]:
        """Call Google Gemini API using REST API directly"""
        import json
        import base64
        import httpx
        
        # Encode images to base64
        image_parts = []
        for path in image_paths:
            with open(path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
                image_parts.append({
                    "inline_data": {
                        "mime_type": "image/jpeg",
                        "data": image_data
                    }
                })
        
        # Add schema to prompt - make it clear we want DATA not the schema
        schema_prompt = f"""{prompt}

IMPORTANT: Extract the ACTUAL DATA from the invoice image and return it in JSON format.

Example of the expected JSON structure (with actual data from the invoice):
{{
  "pagewise_line_items": [
    {{
      "page_no": "1",
      "page_type": "Bill Detail",
      "bill_items": [
        {{
          "item_name": "Product Name Here",
          "item_quantity": 2.0,
          "item_rate": 100.0,
          "item_amount": 200.0
        }}
      ]
    }}
  ]
}}

Return ONLY the JSON with the EXTRACTED DATA from the invoice. No markdown formatting, no code blocks, no schema definitions."""
        
        
        # Build request payload
        payload = {
            "contents": [{
                "parts": [{"text": schema_prompt}] + image_parts
            }],
            "generationConfig": {
                "temperature": self.temperature,
                "maxOutputTokens": settings.max_output_tokens
            }
        }
        
        # Call REST API directly (v1, not v1beta)
        api_key = self.genai._client.api_key if hasattr(self.genai, '_client') else settings.gemini_api_key
        url = f"https://generativelanguage.googleapis.com/v1/models/{self.model_name}:generateContent?key={api_key}"

        # Use longer timeout for large documents
        timeout = max(120.0, len(image_paths) * 30.0)
        logger.info(f"Calling Gemini API with {len(image_paths)} images, timeout={timeout}s")

        response = httpx.post(url, json=payload, timeout=timeout)
        response.raise_for_status()
        
        
        result = response.json()
        response_text = result['candidates'][0]['content']['parts'][0]['text'].strip()

        # Extract token usage from response
        usage_metadata = result.get('usageMetadata', {})
        token_usage = {
            "total_tokens": usage_metadata.get('totalTokenCount', 0),
            "input_tokens": usage_metadata.get('promptTokenCount', 0),
            "output_tokens": usage_metadata.get('candidatesTokenCount', 0)
        }

        # Log raw response for debugging
        logger.info(f"Raw Gemini response length: {len(response_text)} chars")
        logger.debug(f"Raw Gemini response: {response_text[:500]}")
        logger.info(f"Token usage: {token_usage}")

        # Use robust JSON repair
        parsed_json = repair_json(response_text)

        if parsed_json is None:
            logger.error("Failed to parse JSON after all repair attempts")
            logger.error(f"Response text (first 2000 chars): {response_text[:2000]}")
            # Return empty structure instead of raising error
            logger.warning("Returning empty structure due to parse failure")
            return get_empty_invoice_structure(), token_usage

        # Validate structure
        if not validate_invoice_structure(parsed_json):
            logger.warning("Parsed JSON has invalid invoice structure")
            # Check if we have some data
            if parsed_json.get("pagewise_line_items"):
                logger.info(f"Found {len(parsed_json['pagewise_line_items'])} pages despite validation issues, keeping partial data")
            else:
                logger.warning("No valid data found, using empty structure")
                parsed_json = get_empty_invoice_structure()

        return parsed_json, token_usage
    
    def _call_openai(
        self,
        image_paths: List[str],
        prompt: str,
        json_schema: Dict[str, Any]
    ) -> tuple[Dict[str, Any], Dict[str, int]]:
        """Call OpenAI API"""
        # Encode images to base64
        image_contents = []
        for path in image_paths:
            with open(path, "rb") as f:
                base64_image = base64.b64encode(f.read()).decode("utf-8")
                image_contents.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}"
                    }
                })
        
        # Create messages
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt}
                ] + image_contents
            }
        ]
        
        # Call OpenAI with structured output
        response = self.client.beta.chat.completions.parse(
            model=self.model_name,
            messages=messages,
            temperature=self.temperature,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "invoice_extraction",
                    "schema": json_schema,
                    "strict": True
                }
            }
        )
        
        # Extract token usage
        usage = response.usage
        token_usage = {
            "total_tokens": usage.total_tokens,
            "input_tokens": usage.prompt_tokens,
            "output_tokens": usage.completion_tokens
        }
        
        # Parse response
        return json.loads(response.choices[0].message.content), token_usage
    
    def _call_ollama(
        self,
        image_paths: List[str],
        prompt: str,
        json_schema: Dict[str, Any]
    ) -> tuple[Dict[str, Any], Dict[str, int]]:
        """Call Ollama API (local LLM)"""
        import httpx
        
        # Encode images to base64
        images = []
        for path in image_paths:
            with open(path, "rb") as f:
                base64_image = base64.b64encode(f.read()).decode("utf-8")
                images.append(base64_image)
        
        # Add JSON format instructions to prompt (simpler for local models)
        schema_prompt = f"""{prompt}

INSTRUCTIONS:
1. Look at the image carefully.
2. Extract the table of items/products/services.
3. For each row, extract: Description (item_name), Quantity (item_quantity), Rate/Price (item_rate), and Amount (item_amount).
4. If quantity is missing, assume 1.
5. Determine the page type: "Bill Detail", "Final Bill", or "Pharmacy".
6. Return the data as a JSON object.

REQUIRED JSON FORMAT:
{{
  "pagewise_line_items": [
    {{
      "page_no": "1",
      "page_type": "Bill Detail",
      "bill_items": [
        {{
          "item_name": "Example Item",
          "item_quantity": 1.0,
          "item_rate": 100.0,
          "item_amount": 100.0
        }}
      ]
    }}
  ]
}}

Return ONLY the JSON object. No markdown formatting, no code blocks."""

        # Call Ollama API
        payload = {
            "model": self.model_name,
            "prompt": schema_prompt,
            "images": images,
            "stream": False,
            "options": {
                "temperature": self.temperature
            }
        }
        
        response = httpx.post(
            f"{self.base_url}/api/generate",
            json=payload,
            timeout=120.0
        )
        response.raise_for_status()
        
        result = response.json()
        response_text = result.get("response", "")

        # Ollama doesn't provide token counts in the same way, estimate or use 0
        # For local models, token tracking is less critical
        token_usage = {
            "total_tokens": 0,
            "input_tokens": 0,
            "output_tokens": 0
        }

        # Log raw response for debugging
        logger.info(f"Raw Ollama response length: {len(response_text)} chars")
        logger.debug(f"Raw Ollama response: {response_text[:500]}")

        # Use robust JSON repair
        parsed_json = repair_json(response_text)

        if parsed_json is None:
            logger.error("Failed to parse JSON after all repair attempts")
            logger.error(f"Response text (first 2000 chars): {response_text[:2000]}")
            # Return empty structure for Ollama (local models may be less reliable)
            return get_empty_invoice_structure(), token_usage

        # Validate structure
        if not validate_invoice_structure(parsed_json):
            logger.warning("Parsed JSON has invalid invoice structure, using empty structure")
            parsed_json = get_empty_invoice_structure()

        return parsed_json, token_usage
