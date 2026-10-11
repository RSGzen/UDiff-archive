import time
from playwright.sync_api import sync_playwright
import time
import pandas as pd
import os
import sys
# FORCE WINDOWS TO ACCEPT EMOJIS
# This prevents the "charmap codec" error by switching stdout to UTF-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# --- CONFIGURATION ---
FOLDER_NAME = 'jobstreet_scraper'
FILE_NAME = 'job_links.csv'

OUTPUT_FILE_PATH = os.path.join(os.getcwd(), FOLDER_NAME, FILE_NAME)

SEARCH_QUERIES = [
    # Core Engineering
    "Software Engineer", "Backend Developer", "Frontend Developer", 
    "Fullstack Developer", "Mobile Developer", 
    # Niche / High Value
    "Data Scientist", "DevOps Engineer", "Cybersecurity", 
    "Embedded Engineer", "QA Engineer"
    # REMOVED: "Fintech" (skewing data)
]
TARGET_PAGES = 15  # Increased depth to find the "hidden" unsponsored jobs
# ---------------------

def scrape_jobstreet():
    all_jobs = []
    seen_urls = set() 
    
    with sync_playwright() as p:
        # HEADLESS=False is CRITICAL here to see the clicks happening
        browser = p.chromium.launch(headless=False) 
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        for query in SEARCH_QUERIES:
            print(f"\n🔍 SEARCHING: '{query}'...")
            
            # 1. Go to the start page (Page 1)
            q_slug = query.replace(" ", "-")
            base_url = f"https://my.jobstreet.com/{q_slug}-jobs/in-Malaysia"
            
            try:
                print(f"   -> Navigating to Base URL...")
                page.goto(base_url, timeout=30000)
                
                # Check if any jobs exist at all
                try:
                    page.wait_for_selector('a[data-automation="jobTitle"]', timeout=5000)
                except:
                    print("   [No jobs found for this query - Skipping]")
                    continue

                page_num = 1
                
                # 2. THE CLICK LOOP
                while page_num <= TARGET_PAGES:
                    print(f"   -> Scraping Page {page_num}...", end="", flush=True)
                    
                    # Scroll to bottom to trigger lazy loads
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    time.sleep(1) 

                    # --- SCRAPE CURRENT PAGE ---
                    job_elements = page.query_selector_all('article')
                    page_new_count = 0
                    
                    for card in job_elements:
                        # 1. Title & Link
                        title_el = card.query_selector('a[data-automation="jobTitle"]')
                        if not title_el: continue
                        
                        raw_link = title_el.get_attribute('href')
                        title = title_el.inner_text()
                        
                        # Deduplication Check
                        clean_link = raw_link.split('?')[0]
                        if clean_link in seen_urls:
                            continue 
                        seen_urls.add(clean_link)
                        
                        if not clean_link.startswith('http'):
                            full_link = f"https://my.jobstreet.com{clean_link}"
                        else:
                            full_link = clean_link

                        # 2. Company Name
                        company_el = card.query_selector('a[data-automation="jobCompany"]')
                        company = company_el.inner_text() if company_el else "Confidential"

                        # 3. Location
                        location_el = card.query_selector('a[data-automation="jobLocation"]')
                        location = location_el.inner_text() if location_el else "Malaysia"

                        # 4. Salary (Note: Often hidden/empty)
                        salary_el = card.query_selector('span[data-automation="jobSalary"]')
                        salary = salary_el.inner_text() if salary_el else "Not Specified"

                        all_jobs.append({
                            'search_term': query,
                            'title': title,
                            'company': company,
                            'location': location,
                            'salary': salary,
                            'link': full_link
                        })
                        page_new_count += 1
                    
                    print(f" Found {page_new_count} new.")

                    # --- CLICK NEXT ---
                    if page_num >= TARGET_PAGES:
                        break # Stop if we reached our limit

                    try:
                        # Attempt to find the "Next" button
                        # JobStreet 'Next' button usually has 'Next' text or a specific class
                        
                        # Use 'exact=True' to ignore "NEXTDC" or other partial matches
                        next_button = page.get_by_role("link", name="Next", exact=True)
                        
                        # Verify it exists and is visible
                        if next_button.is_visible():
                            next_button.click()
                            page_num += 1
                            
                            # CRITICAL: Wait for the page to actually change
                            # We wait for the URL to change OR a short pause
                            time.sleep(3) 
                        else:
                            print("   [End of Pagination - No Next Button]")
                            break
                            
                    except Exception as e:
                        print(f"   [Pagination Error: {e}]")
                        break
                        
            except Exception as e:
                print(f" Error: {e}")
                continue

        browser.close()
        
    # Final Save
    if all_jobs:
        df = pd.DataFrame(all_jobs)
        print(f"\n✅ SCRAPING COMPLETE")
        print(f"Total Unique Jobs Harvested: {len(df)}")
        df.to_csv(OUTPUT_FILE_PATH, index=False)
    else:
        print("❌ No jobs found.")

if __name__ == "__main__":
    scrape_jobstreet()