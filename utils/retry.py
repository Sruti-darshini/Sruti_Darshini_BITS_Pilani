"""
Retry utilities with exponential backoff for LLM calls
"""
import time
import logging
from typing import Callable, Any, Optional, TypeVar, Dict
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar('T')


def exponential_backoff_retry(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 10.0,
    exponential_base: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    Decorator for retrying function with exponential backoff

    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff
        exceptions: Tuple of exceptions to catch and retry

    Returns:
        Decorated function with retry logic
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            delay = initial_delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    result = func(*args, **kwargs)
                    if attempt > 0:
                        logger.info(f"Success on attempt {attempt + 1} for {func.__name__}")
                    return result

                except exceptions as e:
                    last_exception = e

                    if attempt < max_retries:
                        time.sleep(delay)
                        delay = min(delay * exponential_base, max_delay)
                    else:
                        raise last_exception

            # If we get here, all retries failed
            raise last_exception

        return wrapper
    return decorator


class RetryConfig:
    """Configuration for retry behavior"""

    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 10.0,
        exponential_base: float = 2.0
    ):
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base


def retry_with_config(
    config: RetryConfig,
    func: Callable[..., T],
    *args,
    **kwargs
) -> T:
    """
    Retry a function call with given configuration

    Args:
        config: Retry configuration
        func: Function to call
        *args: Positional arguments for function
        **kwargs: Keyword arguments for function

    Returns:
        Function result

    Raises:
        Last exception if all retries fail
    """
    delay = config.initial_delay
    last_exception = None

    for attempt in range(config.max_retries + 1):
        try:
            result = func(*args, **kwargs)
            if attempt > 0:
                logger.info(f"Success on attempt {attempt + 1} for {func.__name__}")
            return result

        except Exception as e:
            last_exception = e

            if attempt < config.max_retries:
                time.sleep(delay)
                delay = min(delay * config.exponential_base, config.max_delay)
            else:
                logger.error(f"All {config.max_retries + 1} attempts failed: {str(e)}")

    raise last_exception


def should_retry_for_json_error(exception: Exception) -> bool:
    """
    Determine if we should retry based on the exception type

    Args:
        exception: Exception that was raised

    Returns:
        True if we should retry, False otherwise
    """
    # Retry on JSON decode errors
    if isinstance(exception, ValueError) and "JSON" in str(exception):
        return True

    # Retry on specific error messages
    error_msg = str(exception).lower()
    retry_keywords = [
        "unterminated string",
        "json",
        "decode",
        "parse",
        "invalid",
        "timeout",
        "connection",
        "rate limit"
    ]

    return any(keyword in error_msg for keyword in retry_keywords)
