#!/bin/bash
# Configuration
PROJECT_DIR="/Users/rajeshg/.gemini/antigravity/scratch/job_scraper"
PYTHON_EXEC="/Library/Frameworks/Python.framework/Versions/3.13/bin/python3"
LOG_FILE="$PROJECT_DIR/scraper_log.txt"

# Navigate to directory
cd "$PROJECT_DIR"

# Run the python function (checks if already ran today)
echo "$(date): Starting scheduled job..." >> "$LOG_FILE"
$PYTHON_EXEC -c "from improved_job_scraper import run_daily_once; run_daily_once()" >> "$LOG_FILE" 2>&1
echo "$(date): Job finished." >> "$LOG_FILE"
