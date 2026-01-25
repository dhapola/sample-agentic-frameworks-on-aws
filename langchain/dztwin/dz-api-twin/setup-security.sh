#!/bin/bash

# Security Setup Script for AI Chat Widget
# This script installs and configures security tools

set -e

echo "🔒 Setting up security tools..."

# Check if Python is installed
if ! command -v python &> /dev/null; then
    echo "❌ Python 3 is required but not installed"
    exit 1
fi

# Check if pip is installed
if ! command -v pip &> /dev/null; then
    echo "❌ pip is required but not installed"
    exit 1
fi

echo "✅ Python and pip found"

# Install security tools
echo "📦 Installing security tools..."
pip install pre-commit bandit pip-audit detect-secrets

# Initialize pre-commit
echo "🔧 Setting up pre-commit hooks..."

# Check if core.hooksPath is set
HOOKS_PATH=$(git config --get core.hooksPath 2>/dev/null)
if [ -n "$HOOKS_PATH" ]; then
    echo "⚠️  Git core.hooksPath is set to: $HOOKS_PATH"
    echo "Pre-commit requires unsetting this. Options:"
    echo "  1. Unset globally: git config --global --unset core.hooksPath"
    echo "  2. Unset for this repo: git config --unset core.hooksPath"
    echo ""
    read -p "Unset core.hooksPath for this repository? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git config --unset core.hooksPath
        echo "✅ Unset core.hooksPath for this repository"
    else
        echo "⚠️  Skipping pre-commit installation. You can install manually later with:"
        echo "   git config --unset core.hooksPath"
        echo "   pre-commit install"
        SKIP_PRECOMMIT=true
    fi
fi

if [ "$SKIP_PRECOMMIT" != "true" ]; then
    pre-commit install
    echo "✅ Pre-commit hooks installed"
fi

# Create secrets baseline
echo "🔍 Creating secrets baseline..."
detect-secrets scan > .secrets.baseline

# Run initial security audit
echo "🔍 Running initial security audit..."
echo ""
echo "=== Python Dependency Audit ==="
cd backend
pip-audit || echo "⚠️  Some vulnerabilities found - review above"
cd ..

echo ""
echo "=== Python Security Lint (Bandit) ==="
bandit -r backend/ -f screen || echo "⚠️  Some issues found - review above"

# Check for secrets
echo ""
echo "=== Checking for secrets ==="
detect-secrets scan --baseline .secrets.baseline

# Frontend audit (if npm is available)
if command -v npm &> /dev/null; then
    echo ""
    echo "=== Frontend Dependency Audit ==="
    cd frontend
    npm audit || echo "⚠️  Some vulnerabilities found - review above"
    cd ..
fi

echo ""
echo "✅ Security setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Review any vulnerabilities found above"
echo "2. Update .gitignore to exclude sensitive files"
echo "3. Configure environment variables in .env"
echo "4. Review SECURITY.md for best practices"
echo "5. Run 'pre-commit run --all-files' to test hooks"
echo ""
echo "🔒 Security tools installed:"
echo "  - pre-commit: Git hooks for security checks"
echo "  - bandit: Python security linter"
echo "  - pip-audit: Dependency vulnerability scanner"
echo "  - detect-secrets: Secret detection tool"
echo ""
echo "Run 'pre-commit run --all-files' to scan all files"
