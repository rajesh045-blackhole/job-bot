# Daily Job Scraper

## Setup
1.  **Install**:
    ```bash
    pip install -r requirements.txt
    ```
2.  **Config**:
    Update `improved_job_scraper.py` with your Gmail credentials.

## Run
```bash
./run_daily.sh
```

## Auto-Schedule (Mac)
```bash
cp com.rajeshg.jobscraper.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.rajeshg.jobscraper.plist
```
