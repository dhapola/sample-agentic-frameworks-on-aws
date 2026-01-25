@echo off
REM Security Setup Script for AI Chat Widget (Windows)
REM This script installs and configures security tools

echo 🔒 Setting up security tools...

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python 3 is required but not installed
    exit /b 1
)

REM Check if pip is installed
pip --version >nul 2>&1
if errorlevel 1 (
    echo ❌ pip is required but not installed
    exit /b 1
)

echo ✅ Python and pip found

REM Install security tools
echo 📦 Installing security tools...
pip install pre-commit bandit pip-audit detect-secrets

REM Initialize pre-commit
echo 🔧 Setting up pre-commit hooks...
pre-commit install

REM Create secrets baseline
echo 🔍 Creating secrets baseline...
detect-secrets scan > .secrets.baseline

REM Run initial security audit
echo 🔍 Running initial security audit...
echo.
echo === Python Dependency Audit ===
cd backend
pip-audit
cd ..

echo.
echo === Python Security Lint (Bandit) ===
bandit -r backend/ -f screen

REM Check for secrets
echo.
echo === Checking for secrets ===
detect-secrets scan --baseline .secrets.baseline

REM Frontend audit (if npm is available)
where npm >nul 2>&1
if not errorlevel 1 (
    echo.
    echo === Frontend Dependency Audit ===
    cd frontend
    npm audit
    cd ..
)

echo.
echo ✅ Security setup complete!
echo.
echo 📋 Next steps:
echo 1. Review any vulnerabilities found above
echo 2. Update .gitignore to exclude sensitive files
echo 3. Configure environment variables in .env
echo 4. Review SECURITY.md for best practices
echo 5. Run 'pre-commit run --all-files' to test hooks
echo.
echo 🔒 Security tools installed:
echo   - pre-commit: Git hooks for security checks
echo   - bandit: Python security linter
echo   - pip-audit: Dependency vulnerability scanner
echo   - detect-secrets: Secret detection tool
echo.
echo Run 'pre-commit run --all-files' to scan all files

pause
