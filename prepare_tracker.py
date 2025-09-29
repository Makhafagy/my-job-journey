import csv
import os

def prepare_master_file(master_file):
    """
    Checks the master CSV for tracking columns and adds them if they are missing.
    """
    print(f"Checking your master file: '{master_file}'...")

    if not os.path.exists(master_file):
        print(f"Error: The file '{master_file}' was not found. Cannot prepare it.")
        return

    # --- Read the entire file into memory to modify it ---
    with open(master_file, mode='r', encoding='utf-8') as f:
        reader = csv.reader(f)
        try:
            headers = next(reader)
            data_rows = list(reader)
        except StopIteration:
            print("The CSV file is empty. No changes made.")
            return
            
    # --- Check for and add new columns ---
    columns_to_add = {
        'Date Applied': '',  # Default empty value
        'Status': ''        # Default empty value
    }
    
    made_changes = False
    for col_name in columns_to_add:
        if col_name not in headers:
            print(f"'{col_name}' column not found. Adding it to the file...")
            headers.append(col_name)
            for row in data_rows:
                # Add the default empty value to each existing row
                row.append(columns_to_add[col_name])
            made_changes = True

    if not made_changes:
        print("✅ Your file already has all the necessary tracking columns. No changes were needed.")
        return

    # --- Write the modified data back to the same file ---
    with open(master_file, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(data_rows)

    print(f"✅ Successfully updated '{master_file}' with the new columns.")

# --- Main execution block ---
if __name__ == "__main__":
    MASTER_APPLICATIONS_FILE = 'new_grad_swe_apply_links_applying.csv'
    prepare_master_file(MASTER_APPLICATIONS_FILE)