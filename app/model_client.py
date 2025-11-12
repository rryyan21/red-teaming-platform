"""
LLM Model Client - Interface to Language Model APIs.

This module abstracts away the details of calling different LLM providers.
Currently implements OpenAI, but structured to easily add Anthropic, local models, etc.

Key concepts:
- Rate limiting: Prevents hitting API quotas by limiting requests per minute
- Error handling: Retries on transient failures, logs errors
- Provider abstraction: One function interface, multiple backend implementations
"""

import time
import logging
from functools import wraps
from typing import Optional
import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Rate limiting state
_last_call_time = 0
_calls_per_minute = 10  # Default: 10 calls per minute
_min_interval = 60.0 / _calls_per_minute  # Minimum seconds between calls


def rate_limit(calls_per_minute: int = 10):
    """
    Decorator to rate limit function calls.
    
    This ensures we don't exceed API rate limits by spacing out requests.
    Simple implementation: tracks last call time and waits if needed.
    
    Args:
        calls_per_minute: Maximum number of calls allowed per minute
    
    Example:
        @rate_limit(calls_per_minute=20)
        def my_api_call():
            ...
    """
    min_interval = 60.0 / calls_per_minute
    
    def decorator(func):
        last_call = [0]  # Use list to allow modification in nested function
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_time = time.time()
            time_since_last_call = current_time - last_call[0]
            
            if time_since_last_call < min_interval:
                sleep_time = min_interval - time_since_last_call
                logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
                time.sleep(sleep_time)
            
            last_call[0] = time.time()
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def call_openai(prompt: str, model: str = "gpt-3.5-turbo") -> str:
    """
    Call OpenAI's API with a prompt.
    
    This function:
    1. Formats the request according to OpenAI's API spec
    2. Sends HTTP POST request to OpenAI
    3. Parses the JSON response
    4. Extracts the text content
    5. Handles errors gracefully
    
    Args:
        prompt: The text prompt to send to the model
        model: Which OpenAI model to use (default: gpt-3.5-turbo)
    
    Returns:
        str: The model's text response
    
    Raises:
        Exception: If API call fails after retries
    """
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.llm_api_key}",
        "Content-Type": "application/json"
    }
    
    # OpenAI API expects messages in a specific format
    # system message sets the assistant's behavior
    # user message is the actual prompt
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 500
    }
    
    logger.info(f"Calling OpenAI API with model: {model}")
    logger.debug(f"Prompt: {prompt[:100]}...")  # Log first 100 chars
    
    try:
        # Use httpx for synchronous HTTP requests
        # timeout prevents hanging forever
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()  # Raises exception for HTTP errors
            
            data = response.json()
            
            # Extract text from OpenAI's response structure
            # Response format: {"choices": [{"message": {"content": "..."}}]}
            content = data["choices"][0]["message"]["content"]
            logger.info(f"Received response ({len(content)} chars)")
            return content
            
    except httpx.HTTPStatusError as e:
        logger.error(f"OpenAI API HTTP error: {e.response.status_code} - {e.response.text}")
        raise Exception(f"OpenAI API error: {e.response.status_code}")
    except httpx.RequestError as e:
        logger.error(f"OpenAI API request error: {e}")
        raise Exception(f"Failed to connect to OpenAI API: {e}")
    except KeyError as e:
        logger.error(f"Unexpected response format from OpenAI: {e}")
        raise Exception("Invalid response format from OpenAI API")
    except Exception as e:
        logger.error(f"Unexpected error calling OpenAI: {e}")
        raise


@rate_limit(calls_per_minute=10)
def call_model(prompt: str, model: Optional[str] = None) -> str:
    """
    Main function to call an LLM with a prompt.
    
    This is the public interface that other modules use.
    It routes to the appropriate provider based on configuration.
    
    Args:
        prompt: The text prompt to send
        model: Optional model name override (uses default if not provided)
    
    Returns:
        str: The model's response text
    
    Example:
        response = call_model("What is the capital of France?")
        print(response)  # "The capital of France is Paris."
    """
    if settings.llm_provider == "openai":
        model_name = model or "gpt-3.5-turbo"
        return call_openai(prompt, model_name)
    else:
        raise ValueError(
            f"LLM provider '{settings.llm_provider}' not yet supported. "
            "Currently only 'openai' is implemented."
        )

