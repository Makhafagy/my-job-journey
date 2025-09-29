import csv
import os

def count_applications(master_file):
    """
    Reads the master application file and counts the total number of applied jobs.
    """
    print("--- Simple Application Counter ---")
    
    if not os.path.exists(master_file):
        print(f"Error: The master file '{master_file}' was not found.")
        return

    application_count = 0
    
    with open(master_file, mode='r', encoding='utf-8') as f:
        # Use DictReader to easily access columns by name
        reader = csv.DictReader(f)
        
        # Keep a list of the companies you've applied to
        applied_companies = []

        for row in reader:
            # Check if the 'Applied' column exists and is marked TRUE
            if row.get('Applied', 'FALSE').strip().upper() == 'TRUE':
                application_count += 1
                company_name = row.get('company', 'Unknown Company')
                applied_companies.append(company_name)

    # --- Print a detailed summary ---
    print("\n--- Analysis Summary ---")
    print(f"Total Applications Submitted: {application_count}")
    print("--------------------------\n")
    
    if application_count > 0:
        print("Breakdown by Company:")
        # Create a frequency count of each company
        company_counts = {}
        for company in applied_companies:
            company_counts[company] = company_counts.get(company, 0) + 1
        
        # Sort and print the company breakdown
        for company, count in sorted(company_counts.items()):
            print(f"- {company}: {count} application(s)")
            
    print("\n✅ Counting complete.")

# --- Main execution block ---
if __name__ == "__main__":
    MASTER_APPLICATIONS_FILE = 'new_grad_swe_apply_links_applying.csv'
    count_applications(MASTER_APPLICATIONS_FILE)