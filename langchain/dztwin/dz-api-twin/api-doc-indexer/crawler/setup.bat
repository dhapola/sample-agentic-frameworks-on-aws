@echo off

echo Setting up API Doc Crawler...

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

REM Install Playwright browsers
echo Installing Playwright browsers...
playwright install

REM Create .env if not exists
if not exist ".env" (
    echo Creating .env from .env.example...
    copy .env.example .env
    echo Please configure .env with your API documentation URL
)

REM Create data directory
if not exist "data" mkdir data

echo Setup complete! Configure .env and run: python crawler.py
