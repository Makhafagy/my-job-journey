import csv

def run_filter(new_jobs_file, applied_jobs_file, output_file):
    """
    Filters new jobs by removing ones that are marked as 'Applied' in another file.
    """
    
    # --- Step 1: Create a set of URLs for jobs you already applied to ---
    print(f"Reading your master application file: '{applied_jobs_file}'...")
    applied_urls = set()
    try:
        with open(applied_jobs_file, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Check if the 'Applied' column is TRUE
                if row.get('Applied', '').strip().upper() == 'TRUE':
                    # Add the URL to our set of applied jobs
                    applied_urls.add(row['apply_url'])
        
        print(f"Found {len(applied_urls)} jobs you've already applied to.")

    except FileNotFoundError:
        print(f"Error: The file '{applied_jobs_file}' was not found. Please make sure it's in the same directory.")
        return

    # --- Step 2: Filter the new list of scraped jobs ---
    print(f"\nReading the newly scraped jobs from: '{new_jobs_file}'...")
    jobs_to_keep = []
    
    try:
        with open(new_jobs_file, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames  # Get the headers for the output file
            
            for job in reader:
                # Keep the job ONLY if its URL is NOT in our 'applied_urls' set
                if job['apply_url'] not in applied_urls:
                    jobs_to_keep.append(job)

    except FileNotFoundError:
        print(f"Error: The file '{new_jobs_file}' was not found. Please make sure it's in the same directory.")
        return

    # --- Step 3: Write the filtered jobs to a new CSV file ---
    print(f"Found {len(jobs_to_keep)} new jobs to apply for.")
    
    if not jobs_to_keep:
        print("No new jobs to write.")
        return

    with open(output_file, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(jobs_to_keep)

    print(f"✅ Successfully wrote the filtered list to '{output_file}'")


# --- Main execution block ---
if __name__ == "__main__":
    # Define your filenames here
    NEWLY_SCRAPED_FILE = 'new_grad_swe_apply_links.csv'
    MY_APPLICATIONS_FILE = 'new_grad_swe_apply_links_applying.csv'
    # The output file is now the same as the input, so it will be overwritten.
    OUTPUT_FILE = 'new_grad_swe_apply_links.csv'
    
    run_filter(NEWLY_SCRAPED_FILE, MY_APPLICATIONS_FILE, OUTPUT_FILE)