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
    pages_per_chunk: int = 2  # Safe for 512MB RAM - prevents OOM crashes

    # Image Processing (Balanced for 512MB RAM + Good Accuracy)
    pdf_dpi: int = 300  # Lower memory usage while maintaining good quality
    image_quality: int = 100  # Keep max quality for better accuracy
    enable_image_enhancement: bool = False  # Disable to save RAM during processing

    # LLM Settings
    llm_temperature: float = 0.1
    llm_timeout: int = 180  # Longer timeout for large invoices
    max_output_tokens: int = 16384  # Increased for complex invoices
    
    # Logging
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()
