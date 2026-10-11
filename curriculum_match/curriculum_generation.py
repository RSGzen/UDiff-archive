import pandas as pd
import json
import ollama
import time
import datetime
import os
import sys
# FORCE WINDOWS TO ACCEPT UTF-8 (Fixes the \uff08 crash)
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# --- CONFIGURATION ---
INPUT_FOLDER_NAME = 'analyzer'
INPUT_FILE = 'gap_report.json'
INPUT_FILE_PATH = os.path.join(os.getcwd(), INPUT_FOLDER_NAME, INPUT_FILE)

OUTPUT_FOLDER_NAME = 'curriculum_match'
OUTPUT_FILE = 'skill_curriculum_synonyms.json'
OUTPUT_FILE_PATH = os.path.join(os.getcwd(), OUTPUT_FOLDER_NAME, OUTPUT_FILE)

NUM_HARD_SKILLS = 10
NUM_TECH_CONTEXT = 5
NUM_CLASS_NAMES = 25

MODEL_NAME = 'llama3.1'  # Using the smarter 8B model
# ---------------------

def extraction_of_skills(df, num_hard_skills, num_tech_context):
    
    # Obtain list that contains n required hard skill
    hard_skill_lst = []

    hard_skill_df = df['All']['top_hard_skills']

    if len(hard_skill_df) < num_hard_skills:
        raise ValueError(f"Number of hard skill queried is more than available of {len(hard_skill_df)}")

    for n in range(0, num_hard_skills):
        hard_skill_lst.append(hard_skill_df[n]['name'])
    
    # Obtain list that contains n required technical context
    tech_context_lst = []

    tech_context_df = df['All']['top_technical_context']

    if len(tech_context_df) < num_tech_context:
        raise ValueError(f"Number of tech context queried is more than available of {len(tech_context_df)}")

    for n in range(0, num_tech_context):
        tech_context_lst.append(tech_context_df[n]['name'])

    return hard_skill_lst, tech_context_lst

def llm_query(class_subject, num_names):
    # 1. UPDATE THE JSON STRUCTURE DEFINITION
    system_prompt = """
    You are an university professor trying to come out with class names based on the subject. 
    Process the subject name and generate the requested amount of class names in Python list format.
    
    Output ONLY a raw JSON list of strings (e.g., [\"Name1\", \"Name2\"]). 
    Do not include markdown formatting or extra text.
    """

    # 2. UPDATE THE USER PROMPT TO BE SPECIFIC
    user_message = f"""
    Analyze this subject name of '{class_subject}' and come out with {num_names} possible name for this subject.
    
    The context and meaning of the subject must be studied throughly and generated class names must be related to the subject.
    The names provided for the subject can reference to class names such as:
    - Principles of Database Systems
    - Advanced Data Analysis
    - Programming Language C
    - Design and Analysis of Algorithms
    - Applications of Deep Learning

    You can also come out with your own class names that are relevant to the subject and its content.
    """

    # Start timer
    total_start = time.time()
    print(f"Generating class names for {class_subject.ljust(25)}... ", end='')

    try:
        response = ollama.chat(
            model=MODEL_NAME,
            messages=[{'role': 'system',
                       'content': system_prompt},
                      {'role': 'user', 
                       'content': user_message}],
            format='json'
        )

        content = response['message']['content']

        class_list = json.loads(content)
            
        if isinstance(class_list, dict):
            # Sometimes models wrap the list in a key like {"classes": [...]}. Handle that edge case.
            values = list(class_list.values())
            if values and isinstance(values[0], list):
                class_list = values[0]
                
        if isinstance(class_list, list):
            total_duration = time.time() - total_start
            print(f" Completed in {total_duration:.3f}s | Exp: {class_list[0]}")

            return class_list[:num_names] # Ensure strictly 10 items
        else:
            raise ValueError("Model did not return a list.")

    except json.JSONDecodeError:
        print("Error: Failed to parse model output as JSON.")
        return []
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return []

def curriculum_gen():

    # 1. Load Data
    try:
        with open(INPUT_FILE_PATH, 'r') as f:
            data = json.load(f)

        df = pd.DataFrame(data)

        print(f"Loaded {INPUT_FILE} for analysis.")
    
    except Exception as e:
        print(f"Error loading source JSON: {e}")
        return

    # 2. Prepare Report Structure
    report = {
        "generated at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "categories": {}
    }

    # 3. Loop for Main Logic of Curriculum Name Generation
    
    job_types_list = list(df['categories'].keys())

    for i in range(0, len(job_types_list)):
        
        current_job_type = job_types_list[i]

        if current_job_type == 'Other':
            continue

        print(f"\nProcessing skills for {current_job_type} ===> ")

        current_job_details = df['categories'][current_job_type]

        # Obtain list of top n hard skill and top m tech context 
        try:
            hard_skill_lst, tech_context_lst = extraction_of_skills(df=current_job_details, 
                                                                    num_hard_skills=NUM_HARD_SKILLS, 
                                                                    num_tech_context=NUM_TECH_CONTEXT)
        except ValueError as e:
            print(f"Error caught: {e}")

        # Obtain list possible class names
        skill_dict = {}

        for subject in hard_skill_lst:
            data = llm_query(class_subject=subject,
                             num_names=NUM_CLASS_NAMES)
            
            skill_dict[subject] = data 

        for subject in tech_context_lst:
            data = llm_query(class_subject=subject,
                             num_names=NUM_CLASS_NAMES)
            
            skill_dict[subject] = data

        # Save the nested class names to main report 
        report['categories'][current_job_type] = skill_dict

        # Save the report incase it crashes
        with open(OUTPUT_FILE_PATH, 'w') as f:
            json.dump(report, f, indent=4)
            
        print(f"Checkpoint reached {i+1} / {len(job_types_list)}")
    
    # 4. Save to File
    with open(OUTPUT_FILE_PATH, 'w') as f:
        json.dump(report, f, indent=4)
        
    print(f"\n✅ Analysis saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    curriculum_gen()