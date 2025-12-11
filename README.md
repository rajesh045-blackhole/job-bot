# Daily Job Scraper

## Setup
1.  **Install**:
    ```bash
    pip install -r requirements.txt
    ```
2.  **Config**:
    Update `improved_job_scraper.py` with your Gmail credentials.

## Run
### Mac/Linux
```bash
./run_daily.sh
```
### Windows
Double-click `run_daily.bat` or run in CMD.

## Auto-Schedule
### Mac
```bash
cp com.rajeshg.jobscraper.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.rajeshg.jobscraper.plist
```
### Windows
1. Open **Task Scheduler**.
2. Create Basic Task -> Trigger: Daily @ 5 AM.
3. Action: Start a Program -> Select `run_daily.bat`.
4. Finish.
