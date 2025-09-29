import csv
import os
from collections import defaultdict
import datetime

def detailed_analysis(master_file, output_csv_file):
    """
    Reads the master application file, performs a detailed analysis of the application funnel,
    and writes the results to a new CSV file.
    """
    print(f"--- Detailed Application Analysis ---")
    
    # --- Step 1: Read and Tally Data from the Master File ---
    if not os.path.exists(master_file):
        print(f"Error: The master file '{master_file}' was not found. Please run the other scripts first.")
        return

    status_counts = defaultdict(int)
    total_applications = 0

    with open(master_file, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        reader.fieldnames = [name.lower().strip() for name in reader.fieldnames]

        for row in reader:
            if row.get('applied', '').strip().upper() == 'TRUE':
                total_applications += 1
                status = row.get('status', 'applied').strip().lower()
                if not status:
                    status = 'applied'
                status_counts[status] += 1
    
    if total_applications == 0:
        print("No applications found in your master file. Please apply to some jobs first!")
        return

    # --- Step 2: Calculate Key Metrics and Percentages (Updated Logic) ---
    
    # Positive outcomes are interviews and offers. An offer implies an interview.
    interviews = status_counts.get('interview', 0) + status_counts.get('offer', 0)
    offers = status_counts.get('offer', 0)
    
    # NEW LOGIC: "Ghosted" is now calculated as any application that is NOT yet an interview or offer.
    ghosted = total_applications - interviews

    # Calculate rates with the new logic
    interview_rate = (interviews / total_applications) * 100 if total_applications > 0 else 0
    offer_rate = (offers / total_applications) * 100 if total_applications > 0 else 0
    ghosted_rate = (ghosted / total_applications) * 100 if total_applications > 0 else 0

    # --- Step 3: Prepare the Data for Output ---
    analysis_results = [
        {'Metric': 'Total Applications Submitted', 'Value': total_applications},
        {'Metric': '--- Funnel Rates ---', 'Value': '---'},
        {'Metric': 'Interview Rate (%)', 'Value': f'{interview_rate:.2f}'},
        {'Metric': 'Offer Rate (%)', 'Value': f'{offer_rate:.2f}'},
        {'Metric': 'Ghosted Rate (Pending) (%)', 'Value': f'{ghosted_rate:.2f}'}, # Renamed for clarity
        {'Metric': '--- Official Status Breakdown ---', 'Value': '---'},
    ]
    
    # The breakdown still shows the actual statuses you've entered in the file
    for status, count in sorted(status_counts.items()):
        analysis_results.append({'Metric': f'Count: {status.capitalize()}', 'Value': count})

    # --- Step 4: Write the Analysis to the Output CSV File ---
    with open(output_csv_file, mode='w', newline='', encoding='utf-8') as f:
        fieldnames = ['Metric', 'Value']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(analysis_results)

    print(f"\n✅ Analysis complete! A detailed report has been saved to '{output_csv_file}'")


# --- Main execution block ---
if __name__ == "__main__":
    MASTER_APPLICATIONS_FILE = 'new_grad_swe_apply_links_applying.csv'
    ANALYSIS_OUTPUT_FILE = 'application_analysis.csv'
    
    detailed_analysis(MASTER_APPLICATIONS_FILE, ANALYSIS_OUTPUT_FILE)