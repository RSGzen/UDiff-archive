import pandas as pd
import json
import time
import os
import sys
# FORCE WINDOWS TO ACCEPT UTF-8 (Fixes the \uff08 crash)
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# --- CONFIGURATION ---
INPUT_FOLDER_NAME = 'info_extract'
INPUT_FILE = 'job_analysis_final.json'
INPUT_FILE_PATH = os.path.join(os.getcwd(), INPUT_FOLDER_NAME, INPUT_FILE)

OUTPUT_FOLDER_NAME = 'analyzer'
OUTPUT_FILE = 'gap_report.json'
OUTPUT_FILE_PATH = os.path.join(os.getcwd(), OUTPUT_FOLDER_NAME, OUTPUT_FILE)
# ---------------------

SKILL_ALIASES = {
    # Variations : Master Term
    'c programming': 'C',
    'react.js': 'React',
    'reactjs': 'React',
    'node.js': 'Node.js',
    'amazon web services': 'AWS',
    'golang': 'Go',
    'c sharp': 'C#',
    # Add more as you see them
}

def normalize_skill(skill_name):
    s = skill_name.lower().strip()
    for variant, master in SKILL_ALIASES.items():
        if s == variant:
            return master
        
    # Capitalize properly if not in alias list
    return skill_name.title()
    
def categorize_role(title):
    """
    Buckets raw job titles into Standardized Roles based on your new scraping list.
    HIERARCHY MATTERS: We check for specific niches before generic titles.
    """
    
    t = str(title).lower()
    
    # 1. INTERNSHIP & ENTRY
    if any(x in t for x in ['intern', 'trainee', 'student', 'fresh graduate', 'protege']):
        return 'Internship & Entry Level'

    # 2. FULLSTACK
    if any(x in t for x in ['fullstack', 'full-stack', 'mern', 'mean', 'full stack']):
        return 'Fullstack'

    # 3. HIGH SPECIALIZATION (AI / DATA / SECURITY)
    # Fixed: Added 'ai/', 'solution architect'
    if any(x in t for x in ['cyber', 'security', 'infosec', 'penetration', 'soc analyst']):
        return 'Cybersecurity'
    
    if any(x in t for x in ['ai ', 'ai engineer', 'ai/', 'artificial intelligence', 'machine learning', 'deep learning', 'nlp', 'vision', 'data scientist', 'modeler']):
        # Double check it's not "Maintenance" (contains 'ai')
        if 'maint' not in t: 
             return 'AI & Machine Learning'

    if any(x in t for x in ['data', 'analyst', 'business intelligence', 'bi ', 'tableau', 'sql', 'big data']):
        return 'Data & Analytics'

    if any(x in t for x in ['devops', 'sre', 'site reliability', 'ci/cd', 'platform engineer', 'cloud', 'aws', 'azure']):
        return 'Cloud & DevOps'

    # 4. CORE SOFTWARE ENGINEERING
    if any(x in t for x in ['frontend', 'front-end', 'react', 'angular', 'vue', 'web designer', 'ui/ux', 'ui ', 'ux ', 'user interface', 'multimedia']):
        return 'Frontend Web'

    if any(x in t for x in ['backend', 'back-end', 'java', 'spring', 'node', 'php', 'laravel', 'golang', '.net', 'c#']):
        return 'Backend'

    if any(x in t for x in ['qa', 'test', 'quality', 'automation', 'sdet']):
        return 'QA & Testing'

    if any(x in t for x in ['mobile', 'ios', 'android', 'flutter', 'react native', 'app developer']):
        return 'Mobile Development'

    # 5. INFRASTRUCTURE & SUPPORT (Fixed: Added 'noc', 'it engineer')
    if any(x in t for x in ['network', 'infrastructure', 'system engineer', 'sysadmin', 'server', 'noc ']):
        return 'Network & Infrastructure'

    if any(x in t for x in ['support', 'helpdesk', 'service desk', 'it executive', 'technician', 'it engineer', 'operations engineer']):
        return 'IT Support'

    # 6. HARDWARE & MANUFACTURING (Fixed: Added 'service', 'qc', 'electronic', 'yield')
    # This catches the Service Engineers and QC roles
    if any(x in t for x in ['electrical', 'mechanical', 'process', 'manufacturing', 'semiconductor', 'hardware', 'field service', 'service engineer', 'electronic', 'qc ', 'yield', 'smt', 'component', 'maintenance']):
        return 'Hardware & Manufacturing'
        
    if any(x in t for x in ['project', 'product', 'application engineer', 'sales engineer', 'consultant']):
        return 'Project & Sales Engineering'

    if any(x in t for x in ['embedded', 'firmware', 'iot', 'fpga', 'driver']):
        return 'Embedded/Systems'

    # 7. CATCH-ALL (Loosened: Matches 'software' OR 'developer' separately)
    # Catches "Software R&D Engineer"
    if 'software' in t or 'developer' in t or 'programmer' in t or 'engineer' in t:
        # Warning: 'engineer' is broad, but since we filtered all specifics above, 
        # remaining 'engineers' are likely generic software/tech roles.
        return 'General Software Engineering'
        
    return 'Other'

def analyze_market():
    
    # 1. Load Data
    try:
        with open(INPUT_FILE_PATH, 'r') as f:
            data = json.load(f)
        df = pd.DataFrame(data)
        print(f"Loaded {len(df)} jobs for analysis.")

    except Exception as e:
        print(f"Error loading source JSON: {e}")
        return

    # 2. Prepare the Report Structure
    report = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_jobs_analyzed": len(df),
        "job_distribution": {},
        "categories": {}
    }

    # 3. Apply Categorization
    df['category'] = df['job_title'].apply(categorize_role)
    
    # Save overall distribution to report
    dist_counts = df['category'].value_counts()
    report["job_distribution"] = dist_counts.to_dict()
    
    print("\n--- JOB MARKET DISTRIBUTION ---")
    print(dist_counts)

    # 4. Deep Dive per Category
    categories = df['category'].unique()
    
    for cat in categories:
        if cat == 'Other': continue
        
        # Get all jobs in this category
        cat_df = df[df['category'] == cat]
        if len(cat_df) < 3: continue 
        
        print(f"\nProcessing category: {cat}...")
        
        # DEFINE LEVELS TO ANALYZE
        # We will generate a report for 'All' plus specific levels
        levels = {
            'All': cat_df,
            'Junior': cat_df[cat_df['experience_level'].isin(['Junior', 'Internship & Entry Level'])],
            'Mid': cat_df[cat_df['experience_level'] == 'Mid'],
            'Senior': cat_df[cat_df['experience_level'].isin(['Senior', 'Lead'])]
        }
        
        category_report = {}
        
        for level_name, subset in levels.items():
            if len(subset) == 0: continue
            
            # --- A. Salary ---
            avg_min = subset['min_salary'].mean()
            avg_max = subset['max_salary'].mean()
            
            # --- B. Skills & Context (Reused Logic) ---
            # Helper function to get top counts to keep code clean
            def get_top_items(dataframe, column, n=10):
                if column not in dataframe.columns: return []
                exploded = dataframe.explode(column)
                counts = exploded[column].value_counts().head(n)
                return [{"name": k, "count": int(v), "percentage": round((v/len(dataframe))*100, 1)} for k, v in counts.items()]

            # --- SAVE SUB-REPORT ---
            category_report[level_name] = {
                "job_count": int(len(subset)),
                "salary": {
                    "avg_min": int(avg_min) if pd.notna(avg_min) else 0,
                    "avg_max": int(avg_max) if pd.notna(avg_max) else 0
                },
                "top_hard_skills": get_top_items(subset, 'hard_skills'),
                "top_soft_skills": [x['name'] for x in get_top_items(subset, 'soft_skills', 5)],
                "top_technical_context": get_top_items(subset, 'technical_context')
            }

        # Save the nested report to the main object
        report["categories"][cat] = category_report

    # 5. Save to File
    with open(OUTPUT_FILE_PATH, 'w') as f:
        json.dump(report, f, indent=4)
        
    print(f"\n✅ Analysis saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    analyze_market()