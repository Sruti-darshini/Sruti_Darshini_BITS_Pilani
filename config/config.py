"""
Configuration management for Invoice OCR System
"""
from pydantic_settings import BaseSettings
from typing import Literal


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # LLM Provider Configuration
    llm_provider: Literal["gemini", "openai", "ollama"] = "ollama"
    gemini_api_key: str = ""
    openai_api_key: str = ""
    
    # Ollama Configuration
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llava"  # or "llama3.2-vision", "bakllava", etc.
    
    # Model Configuration
    gemini_model: str = "gemini-2.0-flash"
    openai_model: str = "gpt-4o-mini"
    
    # Processing Limits
    max_pages_per_invoice: int = 50
    max_file_size_mb: int = 10
    pages_per_chunk: int = 3  # Process large docs in chunks to avoid truncation

    # Image Processing
    pdf_dpi: int = 300  # DPI for PDF to image conversion (higher = better quality, 200-400 recommended)
    image_quality: int = 95  # JPEG quality (1-100, higher = better)
    enable_image_enhancement: bool = True  # Enable contrast/sharpness enhancement

    # LLM Settings
    llm_temperature: float = 0.1
    llm_timeout: int = 60
    max_output_tokens: int = 8192  # Maximum tokens for LLM response
    
    # Logging
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()
