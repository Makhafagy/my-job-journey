import csv
import os
from collections import defaultdict
import datetime

def load_all_application_data(current_file, past_folder):
    """
    Loads and combines application data from the current file and all CSVs in a past data folder.
    Removes duplicates based on the 'apply_url'.
    """
    all_applications = {} # Use a dictionary to handle duplicates automatically

    # List of files to process
    files_to_process = []
    if os.path.exists(current_file):
        files_to_process.append(current_file)

    # Add files from the past_applied_data folder
    if os.path.exists(past_folder):
        for filename in os.listdir(past_folder):
            if filename.endswith('.csv'):
                files_to_process.append(os.path.join(past_folder, filename))

    # Process all found files
    for file_path in files_to_process:
        try:
            with open(file_path, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Use apply_url as the unique key to handle duplicates
                    if row.get('apply_url'):
                        all_applications[row['apply_url']] = row
        except Exception as e:
            print(f"Warning: Could not read file {file_path}. Error: {e}")

    return list(all_applications.values())


def detailed_analysis(all_data, output_csv_file):
    """
    Performs a detailed analysis of the combined application data.
    """
    print(f"--- Detailed Application Analysis ---")
    
    status_counts = defaultdict(int)
    total_applications = 0

    for row in all_data:
        # Normalize headers by lowercasing keys
        row = {k.lower().strip(): v for k, v in row.items()}
        if row.get('applied', '').strip().upper() == 'TRUE':
            total_applications += 1
            status = row.get('status', 'applied').strip().lower()
            if not status:
                status = 'applied'
            status_counts[status] += 1
    
    if total_applications == 0:
        print("No applications found in your master file or past data folder.")
        return

    # Calculate metrics
    interviews = status_counts.get('interview', 0) + status_counts.get('offer', 0)
    offers = status_counts.get('offer', 0)
    ghosted = total_applications - interviews

    interview_rate = (interviews / total_applications) * 100 if total_applications > 0 else 0
    offer_rate = (offers / total_applications) * 100 if total_applications > 0 else 0
    ghosted_rate = (ghosted / total_applications) * 100 if total_applications > 0 else 0

    analysis_results = [
        {'Metric': 'Total Unique Applications (All Time)', 'Value': total_applications},
        {'Metric': '--- Funnel Rates ---', 'Value': '---'},
        {'Metric': 'Interview Rate (%)', 'Value': f'{interview_rate:.2f}'},
        {'Metric': 'Offer Rate (%)', 'Value': f'{offer_rate:.2f}'},
        {'Metric': 'Ghosted Rate (Pending) (%)', 'Value': f'{ghosted_rate:.2f}'},
        {'Metric': '--- Official Status Breakdown ---', 'Value': '---'},
    ]
    
    for status, count in sorted(status_counts.items()):
        analysis_results.append({'Metric': f'Count: {status.capitalize()}', 'Value': count})

    with open(output_csv_file, mode='w', newline='', encoding='utf-8') as f:
        fieldnames = ['Metric', 'Value']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(analysis_results)

    print(f"\n✅ Analysis complete! A detailed report has been saved to '{output_csv_file}'")


if __name__ == "__main__":
    CURRENT_APPLICATIONS_FILE = 'new_grad_swe_apply_links_applying.csv'
    PAST_DATA_FOLDER = 'past_applied_data'
    ANALYSIS_OUTPUT_FILE = 'application_analysis.csv'
    
    # Load all data first
    all_my_applications = load_all_application_data(CURRENT_APPLICATIONS_FILE, PAST_DATA_FOLDER)
    
    # Run the analysis on the combined data
    detailed_analysis(all_my_applications, ANALYSIS_OUTPUT_FILE)