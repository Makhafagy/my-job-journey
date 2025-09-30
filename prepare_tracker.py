#!/usr/bin/env python3
"""
prepare_tracker.py

Ensure the master CSV has a "Status" column (case-insensitive).
If missing, append the column and write the file back safely.
"""

import csv
import os
import tempfile
import shutil

MASTER_APPLICATIONS_FILE = "new_grad_swe_apply_links.csv"
TRACKER_COLUMN = "Status"

def has_column(headers, col_name):
    """Case-insensitive check if headers contain the column name."""
    return any(h and h.strip().lower() == col_name.strip().lower() for h in headers)

def prepare_master_file(master_file: str):
    print(f"Checking your master file: '{master_file}'...")
    if not os.path.exists(master_file):
        print(f"Error: The file '{master_file}' was not found. Cannot prepare it.")
        return

    # Read file using csv.reader to preserve original ordering/formatting
    with open(master_file, mode="r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        try:
            headers = next(reader)
        except StopIteration:
            print("The CSV file is empty. No changes made.")
            return
        data_rows = list(reader)

    # If Status exists (case-insensitive), do nothing
    if has_column(headers, TRACKER_COLUMN):
        print("✅ Your file already has a 'Status' column. No changes were needed.")
        return

    # Add Status to headers and append empty value to each row
    print(f"'{TRACKER_COLUMN}' column not found. Adding it to the file...")
    headers.append(TRACKER_COLUMN)
    for row in data_rows:
        # Ensure row has same length as headers before appending (some rows might be short)
        while len(row) < len(headers) - 1:
            row.append("")
        row.append("")  # default empty status

    # Write to a temporary file then atomically replace the original
    dir_name = os.path.dirname(os.path.abspath(master_file)) or "."
    fd, tmp_path = tempfile.mkstemp(prefix="tmp_prepare_", suffix=".csv", dir=dir_name)
    os.close(fd)
    try:
        with open(tmp_path, mode="w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(data_rows)
        shutil.move(tmp_path, master_file)
    finally:
        # cleanup leftover temp file if move failed
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass

    print(f"✅ Successfully updated '{master_file}' with the '{TRACKER_COLUMN}' column.")

if __name__ == "__main__":
    prepare_master_file(MASTER_APPLICATIONS_FILE)
