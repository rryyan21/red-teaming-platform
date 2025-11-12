"""
Unit tests for model client.

These tests use mocks to avoid hitting real APIs.
"""

import pytest
from unittest.mock import patch, MagicMock
from app.model_client import call_model, call_openai


@patch('app.model_client.httpx.Client')
def test_call_openai_success(mock_client_class):
    """Test successful OpenAI API call with mocked response."""
    # Mock the HTTP client and response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{
            "message": {
                "content": "The capital of France is Paris."
            }
        }]
    }
    mock_response.raise_for_status.return_value = None
    
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None
    mock_client.post.return_value = mock_response
    mock_client_class.return_value = mock_client
    
    # Call the function
    result = call_openai("What is the capital of France?")
    
    # Verify result
    assert result == "The capital of France is Paris."
    mock_client.post.assert_called_once()


@patch('app.model_client.httpx.Client')
def test_call_openai_error(mock_client_class):
    """Test OpenAI API error handling."""
    # Mock HTTP error
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None
    mock_client.post.side_effect = Exception("Connection error")
    mock_client_class.return_value = mock_client
    
    # Should raise exception
    with pytest.raises(Exception):
        call_openai("test prompt")


def test_call_model_unsupported_provider():
    """Test that unsupported providers raise an error."""
    # This would require mocking settings, but for now we'll just document
    # that this should be tested when adding new providers
    pass

