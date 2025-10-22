# data_loader.py
import json
import pandas as pd
import openpyxl
import gspread
from gspread.exceptions import SpreadsheetNotFound, WorksheetNotFound # New imports
from models import Machine, Job, Operation
import sys # New import for exiting the program

def load_data_from_json(file_path: str):
    # ... (This function remains unchanged)
    with open(file_path, 'r') as f:
        data = json.load(f)
    machines = [Machine(m['machine_id'], [tuple(p) for p in m['unavailable_periods']]) for m in data['machines']]
    jobs = []
    for j_data in data['jobs']:
        ops = [Operation(o['machine_id'], o['processing_time']) for o in j_data['operations']]
        jobs.append(Job(j_data['job_id'], ops, j_data['due_date'], j_data['priority']))
    return machines, jobs

def load_data_from_excel(file_path: str):
    # ... (This function remains unchanged)
    machines_df = pd.read_excel(file_path, sheet_name='Machines')
    jobs_df = pd.read_excel(file_path, sheet_name='Jobs')
    machines = []
    for _, row in machines_df.iterrows():
        unavailable_periods = []
        if pd.notna(row['unavailable_periods']):
            periods_str = str(row['unavailable_periods']).split(';')
            for period in periods_str:
                start, end = map(int, period.split('-'))
                unavailable_periods.append((start, end))
        machines.append(Machine(machine_id=int(row['machine_id']), unavailable_periods=unavailable_periods))
    jobs = []
    for _, row in jobs_df.iterrows():
        operations = []
        if pd.notna(row['operations']):
            ops_str = str(row['operations']).split(';')
            for op in ops_str:
                machine_id, proc_time = op.replace(')', '').split('(')
                operations.append(Operation(int(machine_id), int(proc_time)))
        jobs.append(Job(int(row['job_id']), operations, int(row['due_date']), int(row['priority'])))
    return machines, jobs

# --- MODIFIED FUNCTION FOR TODAY ---
def load_data_from_gsheet(sheet_name: str) -> tuple[list[Machine], list[Job]]:
    """
    Loads machine and job data from a Google Sheet with robust error handling.
    """
    try:
        # Authenticate with Google Sheets API
        gc = gspread.service_account(filename='credentials.json')
        
        # Open the Google Sheet by its name
        spreadsheet = gc.open(sheet_name)
        
        # Get the data from each worksheet
        machines_sheet = spreadsheet.worksheet("Machines")
        machines_df = pd.DataFrame(machines_sheet.get_all_records())
        
        jobs_sheet = spreadsheet.worksheet("Jobs")
        jobs_df = pd.DataFrame(jobs_sheet.get_all_records())

        # --- Parse Machine data ---
        machines = []
        for i, row in machines_df.iterrows():
            if 'machine_id' not in row:
                print(f"Error: 'machine_id' column missing in 'Machines' sheet.")
                sys.exit()
            unavailable_periods = []
            if 'unavailable_periods' in row and row['unavailable_periods']:
                periods_str = str(row['unavailable_periods']).split(';')
                for period in periods_str:
                    if '-' not in period:
                        print(f"Error in 'Machines' sheet, row {i+2}: Invalid format for 'unavailable_periods'. Expected 'start-end'.")
                        sys.exit()
                    start, end = map(int, period.split('-'))
                    unavailable_periods.append((start, end))
            machines.append(Machine(
                machine_id=int(row['machine_id']),
                unavailable_periods=unavailable_periods
            ))

        # --- Parse Job data ---
        jobs = []
        for i, row in jobs_df.iterrows():
            # Check for essential columns
            for col in ['job_id', 'operations', 'due_date', 'priority']:
                if col not in row:
                    print(f"Error: '{col}' column missing in 'Jobs' sheet.")
                    sys.exit()
            
            operations = []
            if 'operations' in row and row['operations']:
                ops_str = str(row['operations']).split(';')
                for op in ops_str:
                    if '(' not in op or ')' not in op:
                        print(f"Error in 'Jobs' sheet, row {i+2}: Invalid format for 'operations'. Expected 'machine(time)'.")
                        sys.exit()
                    machine_id, proc_time = op.replace(')', '').split('(')
                    operations.append(Operation(int(machine_id), int(proc_time)))
            jobs.append(Job(
                job_id=int(row['job_id']),
                operations=operations,
                due_date=int(row['due_date']),
                priority=int(row['priority'])
            ))
            
        return machines, jobs

    # --- Catch specific errors ---
    except FileNotFoundError:
        print("\n--- ERROR ---")
        print("Fatal: 'credentials.json' file not found.")
        print("Please make sure the Google API credentials file is in the same folder as main.py.")
        sys.exit() # Exit the program
    except SpreadsheetNotFound:
        print(f"\n--- ERROR ---")
        print(f"Fatal: Google Sheet named '{sheet_name}' not found.")
        print("Please check the name or share the sheet with your service account email.")
        sys.exit()
    except WorksheetNotFound as e:
        print(f"\n--- ERROR ---")
        print(f"Fatal: A required worksheet is missing from your Google Sheet.")
        print(f"Make sure you have sheets named exactly 'Jobs' and 'Machines'.")
        print(f"Details: {e}")
        sys.exit()
    except Exception as e:
        print(f"\n--- AN UNEXPECTED ERROR OCCURRED ---")
        print(f"Details: {e}")
        print("This could be a data formatting issue in your sheet. Please double-check it.")
        sys.exit()