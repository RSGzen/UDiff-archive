import pandas as pd
import ollama
import json
import os
import re
import time
import hashlib
import sys
# FORCE WINDOWS TO ACCEPT UTF-8 (Fixes the \uff08 crash)
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# --- CONFIGURATION ---
INPUT_FOLDER_NAME = 'jobstreet_scraper'
INPUT_FILE = 'job_details_full.csv'
INPUT_FILE_PATH = os.path.join(os.getcwd(), INPUT_FOLDER_NAME, INPUT_FILE)

OUTPUT_FOLDER_NAME = 'info_extract'
OUTPUT_FILE = 'job_analysis_final.json'
OUTPUT_FILE_PATH = os.path.join(os.getcwd(), OUTPUT_FOLDER_NAME, OUTPUT_FILE)

MODEL_NAME = 'llama3.1'  # Using the smarter 8B model
# ---------------------

def clean_text(text):
    if pd.isna(text): return ""
    
    # 1. Convert to string
    text = str(text)
    
    # 2. Collapse excessive whitespace
    # Replaces 3+ newlines with just 2 (maintaining paragraph breaks but removing huge gaps)
    text = re.sub(r'\n\s*\n', '\n\n', text)
    
    # 3. Strip leading/trailing whitespace
    return text.strip()

def normalize_location(raw_location):
    """
    Derives the State from a specific location string.
    Returns: {'location_raw': str, 'state': str}
    """
    if pd.isna(raw_location):
        return {'location_raw': "Unknown", 'state': "Unknown"}
    
    text = str(raw_location).lower()
    
    # 1. The "Big Bucket" Mappings (80% of your data)
    # Order matters: check specific cities before general states if needed
    
    # KUALA LUMPUR
    if any(x in text for x in ['kuala lumpur', 'kl', 'bangsar', 'bukit jalil', 'cheras']):
        return {'location_raw': raw_location, 'state': 'Kuala Lumpur'}
    
    # SELANGOR (The "Tech Hubs")
    if any(x in text for x in ['selangor', 'petaling jaya', 'pj', 'cyberjaya', 'subang', 'puchong', 'shah alam', 'klang', 'damansara']):
        return {'location_raw': raw_location, 'state': 'Selangor'}
        
    # PENANG
    if any(x in text for x in ['penang', 'pulau pinang', 'georgetown', 'bayan lepas']):
        return {'location_raw': raw_location, 'state': 'Penang'}
        
    # JOHOR
    if any(x in text for x in ['johor', 'jb', 'iskandar']):
        return {'location_raw': raw_location, 'state': 'Johor'}
    
    # 2. Fallback for others
    # If we find the word "Malaysia", but no state, it might be remote or unlisted
    if 'malaysia' in text:
        return {'location_raw': raw_location, 'state': 'Malaysia (General)'}
        
    return {'location_raw': raw_location, 'state': 'Other'}

def parse_salary(salary_str):
    """
    Parses strings like "RM 3,000 - RM 4,500 per month" into structured integers.
    Returns: {'min_salary': int, 'max_salary': int, 'currency': str}
    """
    if pd.isna(salary_str) or 'Hidden' in str(salary_str):
        return {'min_salary': None, 'max_salary': None, 'currency': None}
    
    # 1. Clean the string (remove "per month", commas)
    clean_str = str(salary_str).replace(',', '').upper()
    
    # 2. Extract numbers using Regex
    # This pattern finds digits that might appear in the string
    numbers = re.findall(r'\d+', clean_str)
    numbers = [int(n) for n in numbers]
    
    # 3. Detect Currency (Naive check for MYR/RM)
    currency = 'MYR' if 'RM' in clean_str or 'MYR' in clean_str else 'UNKNOWN'
    
    if not numbers:
        return {'min_salary': None, 'max_salary': None, 'currency': currency}
    
    # 4. Logic for Range vs Single Value
    if len(numbers) == 1:
        return {'min_salary': numbers[0], 'max_salary': numbers[0], 'currency': currency}
    elif len(numbers) >= 2:
        return {'min_salary': min(numbers), 'max_salary': max(numbers), 'currency': currency}
        
    return {'min_salary': None, 'max_salary': None, 'currency': None}

def extract_data(description):
    """Sends the job description to Llama 3 and requests JSON"""

    # 1. UPDATE THE JSON STRUCTURE DEFINITION
    system_prompt = """
    You are an expert technical recruiter. Extract information into strictly valid JSON.
    
    Structure:
    {
        "hard_skills": ["List", "of", "skills"],
        "soft_skills": ["List", "of", "skills"],
        "technical_context": ["List", "of", "domains"],
        "experience_level": "Junior" | "Mid" | "Senior" | "Lead" | "Unknown"
    }
    """

    # 2. UPDATE THE USER PROMPT TO BE SPECIFIC
    user_message = f"""
    Analyze this job description.
    
    1. Extract Hard Skills (Tools, Languages, Frameworks).
    2. Extract Soft Skills.
    3. Extract 'Technical Context': What is the specific application of these skills? 
       - If they ask for Python for AI, is it for 'NLP', 'Computer Vision', or 'Data Engineering'?
       - If they ask for Java, is it for 'Android' or 'Spring Boot Backend'?
       - Be specific but concise (1-3 words per context tag).
    4. Determine Experience Level:
       - "Junior": 0-2 years, Fresh Grad, Entry Level, Intern.
       - "Mid": 3-5 years, "Experienced", or no specific year mentioned but implies autonomy.
       - "Senior": 5+ years, "Senior", "Principal", "Architect".
       - "Lead": Management focus, "Lead", "Manager".
       - "Unknown": If ambiguous.
    
    Job Description:
    {description[:3500]}
    """

    try:
        response = ollama.chat(
            model=MODEL_NAME,
            messages=[{'role': 'system',
                       'content': system_prompt},
                      {'role': 'user', 
                       'content': user_message}],
            format='json',  # <--- THE KEY: Forces valid JSON
        )
        # Parse the string response into a real dictionary
        return json.loads(response['message']['content'])
        
    except Exception as e:
        print(f"Error processing row: {e}")
        return None
    
def generate_fingerprint(text):
    """
    Creates a unique signature for a text block.
    Removes whitespace to ensure formatting differences don't break the match.
    """
    if pd.isna(text):
        return "empty"
    
    # 1. Normalize: Remove all whitespace and make lowercase
    # This ensures that "Python  Developer" and "Python Developer" match
    clean_text = "".join(str(text).split()).lower()
    
    # 2. Hash: Create MD5 signature
    return hashlib.md5(clean_text.encode('utf-8')).hexdigest()

def main():
    print(f"Loading {INPUT_FILE}...")
    
    try:    
        df = pd.read_csv(INPUT_FILE_PATH)
        print(f"Retrieving data for {len(df)} jobs... ")

    except FileNotFoundError:
        print("CSV not found. Did you run the scraper?")
        return
    
    print(f"Initial Raw Count: {len(df)} jobs")

    # --- FILTER LEVEL 1: TECHNICAL DEDUPLICATION (URL) ---
    # Removes "Sticky/Sponsored" ads that appear on multiple pages.
    # We strip query parameters (like ?track=123) to ensure links are truly unique.
    if 'link' in df.columns:
        df['clean_link'] = df['link'].apply(lambda x: str(x).split('?')[0])
        df = df.drop_duplicates(subset='clean_link', keep='first')
        print(f"Count after URL Dedup: {len(df)} (Removed sticky ads)")

    # --- FILTER LEVEL 2: EXACT CONTENT DUPLICATION ---
    # This catches "lazy copy-paste" but allows same description for different TITLES.
    # (e.g. "Frontend Dev" and "Backend Dev" might have same boilerplate, but are diff jobs)
    if 'description' in df.columns:
        # Generate hash
        df['content_hash'] = df['description'].apply(generate_fingerprint)
        
        # We allow duplicate descriptions ONLY IF the 'title' is different.
        # This solves the issue of losing too many jobs.
        df = df.drop_duplicates(subset=['company', 'title', 'content_hash'], keep='first')
        print(f"Count after Content Dedup: {len(df)} (Removed exact duplicates)")

    # Re-indexing DataFrame
    df = df.reset_index(drop=True)
    
    print(f"Final Processing Count: {len(df)} unique jobs")

    print(f"\nStarting extraction on {len(df)} jobs using {MODEL_NAME}...")
    print("This runs on your RTX 4060-Ti. Watch your GPU usage!")

    results = []
    
    # Iterate through the DataFrame
    for index, row in df.iterrows():
        print(f"Processing {index + 1}/{len(df)}: {row['title']}...", end="", flush=True)
        
        t_lower = row['title'].lower()

        # EXCLUSION LIST: Roles that are irrelevant for students/juniors
        if any(x in t_lower for x in ['manager', 'head of', 'director', 'lead', 'principal', 'vp', 'chief']):
            print(" [Skipped - Management-level job not counted]")
            continue # Skip this row, don't count it in stats
        
        # 1. Fast CPU Extraction (Salary and Location)
        salary_data = parse_salary(row['salary'])

        location_data = normalize_location(row['location'])
        
        # 2. Slow GPU Extraction (Skills)
        description = clean_text(row['description'])
        
        if len(description) < 50:
            print(" [Skipped - Description too short]")
            continue

        start_time = time.time()
        data = extract_data(description)
        duration = time.time() - start_time
        
        if data:
            # Add metadata back so we know which job this is
            data['job_title'] = row['title']
            data['company'] = row['company']
            data['location'] = row['location']
            
            data['original_link'] = row['link']

            # Inject the parsed salary
            data.update(salary_data)

            # Inject the location data
            data.update(location_data)

            results.append(data)

            print(f" Done ({duration:.2f}s)")
        else:
            print(" Failed.")

    # Save to JSON

    with open(OUTPUT_FILE_PATH, 'w') as f:
        json.dump(results, f, indent=4)
        
    print(f"\nSuccess! Analyzed {len(results)} jobs.")
    print(f"Data saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()