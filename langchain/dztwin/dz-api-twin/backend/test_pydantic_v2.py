#!/usr/bin/env python3
"""Test script to verify Pydantic V2 validators are working correctly."""

import sys
from main import ChatRequest
from pydantic import ValidationError

def test_message_validator():
    """Test message sanitization validator."""
    print("Testing message validator...")
    
    # Valid message
    request = ChatRequest(message="Hello, how are you?")
    assert request.message == "Hello, how are you?"
    print("✓ Valid message accepted")
    
    # Message with control characters (should be stripped)
    request = ChatRequest(message="Hello\x00World\x01")
    assert "\x00" not in request.message
    assert "\x01" not in request.message
    print("✓ Control characters removed")
    
    # Message with whitespace (should be trimmed)
    request = ChatRequest(message="  Hello World  ")
    assert request.message == "Hello World"
    print("✓ Whitespace trimmed")
    
    # Empty message (should fail validation)
    try:
        ChatRequest(message="")
        assert False, "Empty message should fail"
    except ValidationError:
        print("✓ Empty message rejected")
    
    # Message too long (should fail validation)
    try:
        ChatRequest(message="x" * 5000)
        assert False, "Message too long should fail"
    except ValidationError:
        print("✓ Message too long rejected")

def test_conversation_id_validator():
    """Test conversation ID validator."""
    print("\nTesting conversation_id validator...")
    
    # Valid UUID v4
    request = ChatRequest(
        message="Hello",
        conversation_id="550e8400-e29b-41d4-a716-446655440000"
    )
    assert request.conversation_id == "550e8400-e29b-41d4-a716-446655440000"
    print("✓ Valid UUID v4 accepted")
    
    # None conversation_id (should be allowed)
    request = ChatRequest(message="Hello", conversation_id=None)
    assert request.conversation_id is None
    print("✓ None conversation_id accepted")
    
    # Invalid UUID format (should fail)
    try:
        ChatRequest(message="Hello", conversation_id="not-a-uuid")
        assert False, "Invalid UUID should fail"
    except ValidationError:
        print("✓ Invalid UUID rejected")
    
    # Invalid UUID version (v1 instead of v4 - should fail)
    try:
        ChatRequest(message="Hello", conversation_id="550e8400-e29b-11d4-a716-446655440000")
        assert False, "Non-v4 UUID should fail"
    except ValidationError as e:
        print("✓ Non-v4 UUID rejected")
    
    # Malformed UUID (wrong format)
    try:
        ChatRequest(message="Hello", conversation_id="550e8400-e29b-41d4-a716")
        assert False, "Malformed UUID should fail"
    except ValidationError:
        print("✓ Malformed UUID rejected")

def main():
    """Run all tests."""
    print("=" * 60)
    print("Pydantic V2 Validator Tests")
    print("=" * 60)
    
    try:
        test_message_validator()
        test_conversation_id_validator()
        
        print("\n" + "=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
        return 0
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
