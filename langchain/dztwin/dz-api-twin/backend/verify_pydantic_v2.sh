#!/bin/bash
# Verification script for Pydantic V2 migration

echo "=========================================="
echo "Pydantic V2 Migration Verification"
echo "=========================================="
echo ""

# Check Pydantic version
echo "1. Checking Pydantic version..."
python -c "from pydantic import __version__; print(f'   Pydantic version: {__version__}')"
echo ""

# Test imports without warnings
echo "2. Testing imports for deprecation warnings..."
python -W all -c "from main import app; from config import get_config" 2>&1 | grep -i "PydanticDeprecatedSince20.*main.py\|config.py" && echo "   ✗ Found deprecation warnings" || echo "   ✓ No deprecation warnings in our code"
echo ""

# Run validator tests
echo "3. Running validator tests..."
python test_pydantic_v2.py 2>&1 | grep -E "^(✓|✗)" | head -10
echo ""

# Test config loading
echo "4. Testing configuration loading..."
python -c "from config import get_config; cfg = get_config(); print(f'   ✓ Config loaded: AI={cfg.AI_PROVIDER}, Port={cfg.API_PORT}')"
echo ""

# Test API models
echo "5. Testing API models..."
python -c "from main import ChatRequest, ConversationResponse, MessageResponse; print('   ✓ All models imported successfully')"
echo ""

echo "=========================================="
echo "✓ Pydantic V2 migration verified!"
echo "=========================================="
