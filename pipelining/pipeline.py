import subprocess
import sys
import time
import argparse
import datetime
import os

# --- CONFIGURATION ---
FOLDER_NAME = 'pipelining'
LOG_FILE = "pipeline_log.txt"

# Scripts must be in-order
SCRIPTS = [
    {
        "name": "Job Scraper",
        "folder": "jobstreet_scraper",
        "file": "scraper.py", 
        "description": "Fetching job links from web..."
    },
    {
        "name": "Detail Fetcher",
        "folder": "jobstreet_scraper",
        "file": "scraper_details.py",
        "description": "Visiting each link to get descriptions..."
    },
    {
        "name": "Llama Processor",
        "folder": "info_extract",
        "file": "processor.py",
        "description": "Extracting skills using Llama 3.1..."
    },
    {
        "name": "Market Analyzer",
        "folder": "analyzer",
        "file": "analyzer.py",
        "description": "Generating Gap Analysis Report..."
    }
]
# ---------------------

def tee_output(process, log_handle):
    """
    Reads stdout from a subprocess line-by-line.
    - File: Always saves pure UTF-8 (Emojis intact).
    - Console: Tries to print UTF-8, but strips emojis if Windows complains.
    """
    for line in iter(process.stdout.readline, ''):
        if line:
            # 1. Safe Print to Console
            try:
                # Try printing normally
                print(line.rstrip())
            except UnicodeEncodeError:
                # If Windows crashes on an emoji, strip it and print the ASCII version
                # This ensures the pipeline keeps running even if the display is ugly
                safe_text = line.encode('ascii', 'ignore').decode('ascii')
                print(safe_text.rstrip())
            
            # 2. Write to File (Always works because we opened it with encoding='utf-8')
            try:
                log_handle.write(line)
                log_handle.flush()
            except Exception as e:
                print(f"[Log Error: {e}]")

def run_step(script_info, log_handle):
    """Runs a script and streams output to both targets"""
    header = f"\n{'='*60}\n🚀 STEP: {script_info['name']}\nℹ️  {script_info['description']}\n{'='*60}\n"
    
    # Write Header to both
    print(header, end='')
    log_handle.write(header)
    
    start_time = time.time()
    
    # Create file path
    execution_file_path = os.path.join(os.getcwd(), script_info['folder'], script_info['file'])

    try:
        # Popen allows us to stream output in real-time
        # bufsize=1 means line-buffered (smooth output)
        process = subprocess.Popen(
            [sys.executable, execution_file_path], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT, # Redirect errors to standard output so they get logged too
            text=True,
            bufsize=1,
            encoding='utf-8', # Force UTF-8 for emoji support
            errors='replace'
        )
        
        # Start the dual-streamer
        tee_output(process, log_handle)
        
        # Wait for finish
        return_code = process.wait()
        
        duration = time.time() - start_time
        footer = f"\n✅ {script_info['name']} COMPLETED in {duration:.2f} seconds.\n"
        
        if return_code == 0:
            print(footer)
            log_handle.write(footer)
            return True
        else:
            error_msg = f"\n❌ ERROR: {script_info['name']} failed with exit code {return_code}.\n"
            print(error_msg)
            log_handle.write(error_msg)
            return False
            
    except FileNotFoundError:
        msg = f"\n❌ ERROR: Could not find file '{script_info['file']}'.\n"
        print(msg)
        log_handle.write(msg)
        return False

def main():
    parser = argparse.ArgumentParser(description="UDiff Data Pipeline")
    parser.add_argument("--skip-scrape", action="store_true", help="Skip the scraping step.")
    args = parser.parse_args()

    # Create file path
    log_file_path = os.path.join(os.getcwd(), FOLDER_NAME, LOG_FILE)

    # Open the log file once at the start
    # 'a' mode appends to history. Use 'w' if you want to overwrite every time.
    with open(log_file_path, 'w', encoding='utf-8') as log_file:
        
        # Timestamp the run
        start_timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        intro = f"🤖 STARTING UDIFF PIPELINE RUN AT {start_timestamp}\n"
        print(intro)
        log_file.write(intro)
        
        total_start = time.time()
        
        for script in SCRIPTS:
            if args.skip_scrape and "scraper" in script['file'].lower():
                skip_msg = f"\n⏭️  Skipping {script['name']} (User requested skip)...\n"
                print(skip_msg)
                log_file.write(skip_msg)
                continue
                
            success = run_step(script, log_file)
            if not success:
                print("🛑 Pipeline stopped due to error.")
                log_file.write("🛑 Pipeline stopped due to error.\n")
                sys.exit(1)

        total_duration = time.time() - total_start
        outro = f"\n{'='*60}\n🎉 PIPELINE FINISHED SUCCESSFULLY\n⏱️  Total Run Time: {total_duration/60:.2f} minutes\n{'='*60}\n"
        print(outro)
        log_file.write(outro)

    print(f"\n📄 Full log saved to: {LOG_FILE}")

if __name__ == "__main__":
    main()