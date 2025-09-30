import csv
import os

def load_all_application_data(current_file, past_folder):
    """
    Loads and combines application data from the current file and all CSVs in a past data folder.
    Removes duplicates based on the 'apply_url'.
    """
    all_applications = {} # Use a dictionary to handle duplicates automatically

    files_to_process = []
    if os.path.exists(current_file):
        files_to_process.append(current_file)

    if os.path.exists(past_folder):
        for filename in os.listdir(past_folder):
            if filename.endswith('.csv'):
                files_to_process.append(os.path.join(past_folder, filename))

    for file_path in files_to_process:
        try:
            with open(file_path, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get('apply_url'):
                        all_applications[row['apply_url']] = row
        except Exception as e:
            print(f"Warning: Could not read file {file_path}. Error: {e}")

    return list(all_applications.values())


def count_applications(all_data):
    """
    Reads the combined application data and counts the total number of applied jobs.
    """
    print("--- Simple Application Counter (All Time) ---")
    
    application_count = 0
    applied_companies = []

    for row in all_data:
        # Normalize headers by lowercasing keys
        row = {k.lower().strip(): v for k, v in row.items()}
        if row.get('applied', 'FALSE').strip().upper() == 'TRUE':
            application_count += 1
            company_name = row.get('company', 'Unknown Company')
            applied_companies.append(company_name)

    print("\n--- Analysis Summary ---")
    print(f"Total Unique Applications Submitted: {application_count}")
    print("--------------------------\n")
    
    if application_count > 0:
        print("Breakdown by Company:")
        company_counts = {}
        for company in applied_companies:
            company_counts[company] = company_counts.get(company, 0) + 1
        
        for company, count in sorted(company_counts.items()):
            print(f"- {company}: {count} application(s)")
            
    print("\n✅ Counting complete.")


if __name__ == "__main__":
    CURRENT_APPLICATIONS_FILE = 'new_grad_swe_apply_links_applying.csv'
    PAST_DATA_FOLDER = 'past_applied_data'

    # Load all data first
    all_my_applications = load_all_application_data(CURRENT_APPLICATIONS_FILE, PAST_DATA_FOLDER)
    
    # Run the count on the combined data
    count_applications(all_my_applications)