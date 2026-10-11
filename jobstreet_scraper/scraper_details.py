import time
import os
import pandas as pd
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import sys
# Force output to UTF-8 to prevent pipeline crashes
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# --- CONFIGURATION ---
INPUT_FOLDER_NAME = 'jobstreet_scraper'
INPUT_FILE = 'job_links.csv'
INPUT_FILE_PATH = os.path.join(os.getcwd(), INPUT_FOLDER_NAME, INPUT_FILE)

OUTPUT_FOLDER_NAME = 'jobstreet_scraper'
OUTPUT_FILE = 'job_details_full.csv'
OUTPUT_FILE_PATH = os.path.join(os.getcwd(), OUTPUT_FOLDER_NAME, OUTPUT_FILE)
# ---------------------

def scrape_details():
    # 1. Load the links we harvested

    try:
        df = pd.read_csv(INPUT_FILE_PATH)
        print(f"Loaded {len(df)} jobs to process.")

    except FileNotFoundError:
        print(f"Error: '{INPUT_FILE}' not found. Run scraper.py first.")
        return

    # Create a column for the new data if it doesn't exist
    if 'description' not in df.columns:
        df['description'] = ""

    with sync_playwright() as p:
        # headless=True is faster, but keep False if you want to watch it work
        browser = p.chromium.launch(headless=False) 
        page = browser.new_page()

        # 2. Iterate through the links
        for index, row in df.iterrows():
            # Skip if we already have the description (allows restarting crashed scripts)
            if pd.notna(row['description']) and row['description'] != "":
                continue

            url = row['link']
            print(f"[{index+1}/{len(df)}] Visiting: {row['title']}...")

            try:
                page.goto(url, timeout=60000) # 60s timeout for slow pages
                
                # Wait for the description to load
                page.wait_for_selector('div[data-automation="jobAdDetails"]', timeout=5000)
                
                # Extract HTML
                html = page.content()
                soup = BeautifulSoup(html, 'html.parser')

                # 3. Target the Description Container
                # JobStreet standard tag for the body text
                desc_div = soup.find('div', attrs={"data-automation": "jobAdDetails"})
                
                if desc_div:
                    # distinct separator to keep structure clean
                    full_text = desc_div.get_text(separator="\n").strip() 
                    df.at[index, 'description'] = full_text
                    print("   -> Success: Extracted description.")
                else:
                    print("   -> Warning: Description container not found.")
                    df.at[index, 'description'] = "Error: Not Found"

            except Exception as e:
                print(f"   -> Error visiting page: {e}")
                df.at[index, 'description'] = "Error: Timeout/Fail"

            # 4. Respectful Delay & Save Checkpoint
            # Don't hammer their server; sleep 1-2 seconds
            time.sleep(1) 
            
            # Save every 5 rows so we don't lose data if it crashes
            if index % 5 == 0:
                df.to_csv(OUTPUT_FILE_PATH, index=False)
                print("   [Checkpoint Saved]")

        browser.close()

    # Final Save
    df.to_csv(OUTPUT_FILE_PATH, index=False)
    print("\n--- EXTRACTION COMPLETE ---")
    print(f"Data saved to '{OUTPUT_FILE}'")

if __name__ == "__main__":
    scrape_details()