import pandas as pd
import json
import os
from analyzer import categorize_role # Import your existing logic

# --- CONFIGURATION ---
INPUT_FOLDER_NAME = 'info_extract'
INPUT_FILE = 'job_analysis_final.json'
INPUT_FILE_PATH = os.path.join(os.getcwd(), INPUT_FOLDER_NAME, INPUT_FILE)

# Load your processed data
try:
    with open(INPUT_FILE_PATH, 'r') as f:
        
        data = json.load(f)
    df = pd.DataFrame(data)
    
    # Apply your current categorization
    df['category'] = df['job_title'].apply(categorize_role)
    
    # Filter for 'Other' and count the top titles
    others = df[df['category'] == 'Other']
    print(f"--- Top 30 Unclassified Job Titles (Total: {len(others)}) ---")
    print(others['job_title'].value_counts().head(30))
    
except Exception as e:
    print(f"Error: {e}")