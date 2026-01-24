@echo off

echo Setting up API Doc Ingester...

REM Create virtual environment
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

REM Create .env if not exists
if not exist ".env" (
    echo Creating .env from .env.example...
    copy .env.example .env
    echo Please configure .env with your embedding provider settings
)

echo Setup complete! Configure .env and run: python ingest.py
