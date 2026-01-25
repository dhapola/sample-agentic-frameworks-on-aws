"""
Data sanitization utilities for logging and security
"""
import re
from typing import Optional


def redact_pii(text: str, max_length: Optional[int] = None) -> str:
    """
    Redact personally identifiable information from text
    
    Args:
        text: Text to redact
        max_length: Optional maximum length to truncate to
        
    Returns:
        Redacted text
    """
    if not text:
        return text
    
    # Redact email addresses
    text = re.sub(
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        '[EMAIL_REDACTED]',
        text
    )
    
    # Redact phone numbers (various formats)
    text = re.sub(
        r'\b(?:\+?1[-.]?)?\(?([0-9]{3})\)?[-.]?([0-9]{3})[-.]?([0-9]{4})\b',
        '[PHONE_REDACTED]',
        text
    )
    
    # Redact SSN (US Social Security Numbers)
    text = re.sub(
        r'\b\d{3}-\d{2}-\d{4}\b',
        '[SSN_REDACTED]',
        text
    )
    
    # Redact credit card numbers (basic pattern)
    text = re.sub(
        r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
        '[CARD_REDACTED]',
        text
    )
    
    # Redact IP addresses
    text = re.sub(
        r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b',
        '[IP_REDACTED]',
        text
    )
    
    # Redact API keys and tokens (common patterns)
    text = re.sub(
        r'\b[A-Za-z0-9]{32,}\b',
        '[TOKEN_REDACTED]',
        text
    )
    
    # Truncate if max_length specified
    if max_length and len(text) > max_length:
        text = text[:max_length] + '...[TRUNCATED]'
    
    return text


def sanitize_for_logging(text: str, max_length: int = 200) -> str:
    """
    Sanitize text for safe logging (redact PII + truncate)
    
    Args:
        text: Text to sanitize
        max_length: Maximum length (default 200 chars)
        
    Returns:
        Sanitized text safe for logging
    """
    return redact_pii(text, max_length=max_length)


def sanitize_error_message(error: Exception) -> str:
    """
    Sanitize error messages to avoid exposing sensitive information
    
    Args:
        error: Exception object
        
    Returns:
        Safe error message for client
    """
    error_str = str(error)
    
    # Remove file paths
    error_str = re.sub(r'[/\\][\w/\\.-]+', '[PATH]', error_str)
    
    # Remove stack traces
    if 'Traceback' in error_str or 'File "' in error_str:
        return "An internal error occurred. Please try again."
    
    # Redact PII
    error_str = redact_pii(error_str, max_length=100)
    
    return error_str
