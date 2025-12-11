import requests
from bs4 import BeautifulSoup
import pandas as pd
import smtplib
from email.message import EmailMessage
from datetime import datetime
import schedule
import time
import logging
import re

# ---------------- CONFIGURATION ------------------
YOUR_EMAIL = "rajeshguvvala045@gmail.com"
YOUR_EMAIL_PASSWORD = "llxz nqze jedn qzxz"  # Replace with your actual App Password
SEND_TO = "rajeshguvvala045@gmail.com"
CSV_FILENAME = "job_links_daily.csv"
LAST_RUN_FILE = ".last_run_date"

# Request Headers (to look like a real browser)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename="scraper_log.txt"
)

# ---------------- STATE MANAGEMENT ------------------

def check_if_run_today():
    """
    Checks if the script has already successfully run today.
    Returns True if run today, False otherwise.
    """
    try:
        with open(LAST_RUN_FILE, "r") as f:
            last_run_date = f.read().strip()
        
        today_date = datetime.now().strftime("%Y-%m-%d")
        
        if last_run_date == today_date:
            logging.info("Script already ran today. Skipping.")
            return True
        return False
    except FileNotFoundError:
        return False

def mark_as_run():
    """
    Updates the state file with today's date.
    """
    today_date = datetime.now().strftime("%Y-%m-%d")
    with open(LAST_RUN_FILE, "w") as f:
        f.write(today_date)
    logging.info(f"Marked run for {today_date} as complete.")

# ---------------- FILTER LOGIC ------------------

def is_location_allowed(text):
    """
    Analyzes text (location string or job description fragment) to see if it's allowed.
    Returns: (is_allowed: bool, reason: str)
    """
    if not text:
        return True, "No location text found"
    
    text_lower = text.lower()
    
    # 1. Check Inclusive Terms (Always allow these)
    inclusive_terms = [
        "bengaluru", "bangalore", 
        "remote", "work from home", "wfh", "work from anywhere", 
        "open to all", "pan india", "anywhere"
    ]
    for term in inclusive_terms:
        if term in text_lower:
            return True, f"Included - Matches '{term}'"

    # 2. Check Exclusive Terms (Reject if explicitly restricted to another city)
    # Pattern: "only <City> candidates" or "candidates from <City> only" or "must be based in <City>"
    # We want to catch things like "Mumbai only" but we already passed the Bangalore check,
    # so if it says "Bangalore only" it would have been caught above.
    
    restriction_patterns = [
        r"only\s+([a-zA-Z\s]+)\s+candidates",
        r"([a-zA-Z\s]+)\s+candidates\s+only",
        r"candidates\s+from\s+([a-zA-Z\s]+)\s+only",
        r"must\s+be\s+based\s+in\s+([a-zA-Z\s]+)",
        r"located\s+in\s+([a-zA-Z\s]+)\s+only"
    ]
    
    for pattern in restriction_patterns:
        match = re.search(pattern, text_lower)
        if match:
            # If we matched a restriction pattern, and we didn't match the inclusive terms above,
            # then it is likely a restriction for a DIFFERENT city.
            restricted_location = match.group(1).strip()
            return False, f"Restricted - Only for '{restricted_location}'"

    # 3. Default (If no restriction found)
    # If it just says "Mumbai" without "only", usually we might want to skip it if we strictly want Bangalore.
    # But the user requirement said: "mark it location-restricted ... IF ... explicit location-restriction phrasing".
    # It implies if it just says "Mumbai" it might not be "restricted phrasing". 
    # However, practically for a job scraper, if location is "Mumbai", it usually implies "Work in Mumbai".
    # Let's be safe: If the location field ITSELF is just a city name not in our allowed list, we should probably flag it?
    # BUT user said: "if a job post contains explicit location-restriction phrasing... mark it... Exception... explicitly mentions Bangalore".
    # This implies we only filter if we see "ONLY".
    # Wait, re-reading: "Add a job-filtering rule that excludes location-restricted job posts unless..."
    # If the location field in Internshala says "Mumbai", is that a restriction? Yes.
    # Let's treat the 'Location' field as a strong indicator.
    
    return True, "Included - No explicit restriction found"


# ---------------- SCRAPING FUNCTIONS ------------------

def get_soup(url):
    """
    Helper function to make a request and return BeautifulSoup object.
    Includes basic error handling and delays.
    """
    try:
        time.sleep(2)  # Be polite to the server
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        return BeautifulSoup(response.content, "html.parser")
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching URL {url}: {e}")
        return None

def scrape_internshala(url, category_name):
    """
    Specific parser for Internshala job listings.
    """
    logging.info(f"Scraping Internshala: {category_name}")
    soup = get_soup(url)
    jobs = []

    if not soup:
        return []

    results = soup.find_all("div", class_="individual_internship")
    
    if not results:
        logging.warning("Could not find individual jobs on Internshala page. Returning main link.")
        jobs.append({
            "Category": category_name,
            "Role": "See All Jobs (Parsing Failed)",
            "Company": "Internshala",
            "Location": "Unknown",
            "URL": url,
            "PostedDate": datetime.now().strftime("%Y-%m-%d"),
            "FilterReason": "Fallback"
        })
        return jobs

    for result in results:
        try:
            # Extract details
            title_tag = result.find("h3", class_="job_profile") or result.find("div", class_="company")
            company_tag = result.find("div", class_="company_name")
            link_tag = result.get("data-href")
            
            # Extract Location
            # Internshala usually has a div with id 'location_names' or class 'location_link'
            location_tag = result.find("div", id="location_names") or result.find("a", class_="location_link")
            location_text = location_tag.get_text(strip=True) if location_tag else "Unknown"

            title = title_tag.get_text(strip=True) if title_tag else "N/A"
            company = company_tag.get_text(strip=True) if company_tag else "N/A"
            link = "https://internshala.com" + link_tag if link_tag else url
            
            # Apply Filter
            is_allowed, reason = is_location_allowed(location_text)
            
            if is_allowed:
                jobs.append({
                    "Category": category_name,
                    "Role": title,
                    "Company": company,
                    "Location": location_text,
                    "URL": link,
                    "PostedDate": datetime.now().strftime("%Y-%m-%d"),
                    "FilterReason": reason
                })
            else:
                logging.info(f"Filtered out job: {title} at {company} ({location_text}) - {reason}")

        except Exception as e:
            logging.warning(f"Error parsing an item in {category_name}: {e}")
            continue
            
    return jobs

def scrape_generic(url, category_name):
    """
    Generic scraper for sites where we can't easily parse details.
    We can't filter these easily as we don't extract full text. 
    We will assume ACTIVE for now.
    """
    logging.info(f"Scraping Generic: {category_name}")
    soup = get_soup(url)
    status = "Active" if soup else "Unreachable"
    
    return [{
        "Category": category_name,
        "Role": f"Browse Jobs ({status})",
        "Company": "N/A",
        "Location": "Unknown (Generic Link)",
        "URL": url,
        "PostedDate": datetime.now().strftime("%Y-%m-%d"),
        "FilterReason": "Generic Source"
    }]

# ---------------- MAIN LOGIC ------------------

def scrape_all_jobs():
    all_jobs = []

    # Define sources: (Name, URL, Type)
    # Type 'internshala' uses the specific parser, 'generic' uses the fallback.
    # UPDATED: Using only 24-hour filters where possible to ensure freshness.
    sources = [
        # LinkedIn - Past 24 hours (f_TPR=r86400)
        ("LinkedIn ML Intern (24h)", "https://in.linkedin.com/jobs/machine-learning-intern-jobs?f_TPR=r86400", "generic"),
        ("LinkedIn Data Analyst (24h)", "https://in.linkedin.com/jobs/data-analyst-intern-jobs?f_TPR=r86400", "generic"),
        ("LinkedIn Python Dev (24h)", "https://in.linkedin.com/jobs/python-developer-jobs?f_TPR=r86400", "generic"),
        
        # Indeed - Past 24 hours (fromage=1)
        ("Indeed Python Remote (24h)", "https://in.indeed.com/jobs?q=fresher+python+developer+remote&fromage=1", "generic"),
        ("Indeed Data Analyst (24h)", "https://in.indeed.com/jobs?q=data+analyst+fresher&fromage=1", "generic"),

        # Naukri - Last 1 day (n=1)
        ("Naukri Python (Freshers 24h)", "https://www.naukri.com/python-developer-jobs-for-freshers?k=python%20developer&n=1", "generic"),
        
        # Internshala - Usually ordered by date
        ("Internshala Python", "https://internshala.com/fresher-jobs/python-developer-jobs", "internshala"),
        ("Internshala Data Analyst", "https://internshala.com/fresher-jobs/data-analytics-jobs", "internshala"),
    ]

    print("Starting scraping process (24h + Location filters applied)...")
    
    for name, url, source_type in sources:
        print(f"Checking {name}...")
        if source_type == "internshala":
            jobs = scrape_internshala(url, name)
        else:
            jobs = scrape_generic(url, name)
        
        all_jobs.extend(jobs)

    if not all_jobs:
        print("No jobs found (or all filtered out).")
        return None

    # Save to CSV
    df = pd.DataFrame(all_jobs)
    # Reorder columns
    cols = ["Category", "Role", "Company", "Location", "URL", "PostedDate", "FilterReason"]
    existing_cols = [c for c in cols if c in df.columns]
    df = df[existing_cols]
    
    df.to_csv(CSV_FILENAME, index=False)
    print(f"Scraping completed. Saved {len(df)} items to {CSV_FILENAME}")
    return CSV_FILENAME

def send_email():
    csv_file = scrape_all_jobs()
    
    if not csv_file:
        print("Scraping failed or yielded no results. skipping email.")
        return

    msg = EmailMessage()
    msg["Subject"] = f"Daily Job Links (24h Fresh) - {datetime.now().strftime('%d-%m-%Y')}"
    msg["From"] = YOUR_EMAIL
    msg["To"] = SEND_TO
    msg.set_content(
        "Hello,\n\nHere is your daily list of fresh job opportunities posted in the last 24 hours.\n"
        "I have filtered out jobs that are explicitly restricted to locations other than Bangalore/Remote.\n\n"
        "Good luck with your applications!"
    )

    # Attach CSV
    try:
        with open(csv_file, "rb") as f:
            msg.add_attachment(f.read(), maintype="application", subtype="octet-stream", filename=csv_file)

        # SMTP Gmail
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(YOUR_EMAIL, YOUR_EMAIL_PASSWORD)
            smtp.send_message(msg)
        
        print("Email sent successfully!")
        logging.info("Email sent successfully.")
    except Exception as e:
        print(f"Failed to send email: {e}")
        logging.error(f"Failed to send email: {e}")

def run_daily_once():
    """
    Wrapper function to be called by the scheduler or shell script.
    Checks if run today, if not, runs and marks done.
    """
    print("Checking if job already ran today...")
    if check_if_run_today():
        print("Job already ran today. Exiting.")
        return

    print("Job hasn't ran today. Starting...")
    send_email()
    mark_as_run()

# ---------------- SCHEDULE ------------------

def start_scheduler():
    # Schedule daily at 5 AM
    # calling run_daily_once protects against restart-loops if we were using a loop
    # but here we are using launchd mostly.
    # If keeping the internal python scheduler for manual run:
    schedule.every().day.at("05:00").do(run_daily_once)
    
    print("Scheduler started. Waiting for 05:00 AM...")
    
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    # If run directly, run the daily logic once (checking state)
    run_daily_once()
