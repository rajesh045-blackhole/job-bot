@echo off
:: Navigate to the script's directory
cd /d "%~dp0"

:: Run the python function (checks if already ran today)
:: Ensure 'python' is in your PATH
python -c "from improved_job_scraper import run_daily_once; run_daily_once()" >> scraper_log.txt 2>&1
