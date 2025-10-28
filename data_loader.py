# data_loader.py
"""
Handles all data loading for the application.
Supports loading from Google Sheets, Excel, or JSON.
Includes robust error handling for API connections and data formats.
"""
import pandas as pd
import openpyxl
import gspread
from gspread.exceptions import SpreadsheetNotFound, WorksheetNotFound
from models import Machine, Job, Operation
import sys
import json

def load_data_from_gsheet(sheet_name: str) -> tuple[list[Machine], list[Job]]:
    """Loads machine and job data from a Google Sheet."""
    # ... (code for loading from Google Sheets) ...
    try:
        gc = gspread.service_account(filename='credentials.json')
        spreadsheet = gc.open(sheet_name)
        machines_sheet = spreadsheet.worksheet("Machines")
        machines_df = pd.DataFrame(machines_sheet.get_all_records())
        jobs_sheet = spreadsheet.worksheet("Jobs")
        jobs_df = pd.DataFrame(jobs_sheet.get_all_records())
        machines = []
        for i, row in machines_df.iterrows():
            if 'machine_id' not in row: sys.exit("Error: 'machine_id' missing in 'Machines' sheet.")
            unavailable_periods = []
            if 'unavailable_periods' in row and row['unavailable_periods']:
                periods_str = str(row['unavailable_periods']).split(';')
                for period in periods_str:
                    if '-' not in period: sys.exit(f"Error in 'Machines' row {i+2}: Invalid 'unavailable_periods' format.")
                    start, end = map(int, period.split('-'))
                    unavailable_periods.append((start, end))
            machines.append(Machine(int(row['machine_id']), unavailable_periods))
        jobs = []
        for i, row in jobs_df.iterrows():
            for col in ['job_id', 'operations', 'due_date', 'priority']:
                if col not in row: sys.exit(f"Error: '{col}' missing in 'Jobs' sheet.")
            operations = []
            if 'operations' in row and row['operations']:
                ops_str = str(row['operations']).split(';')
                for op in ops_str:
                    if '(' not in op or ')' not in op: sys.exit(f"Error in 'Jobs' row {i+2}: Invalid 'operations' format.")
                    machine_id, proc_time = op.replace(')', '').split('(')
                    operations.append(Operation(int(machine_id), int(proc_time)))
            jobs.append(Job(int(row['job_id']), operations, int(row['due_date']), int(row['priority'])))
        return machines, jobs
    except FileNotFoundError: sys.exit("Fatal: 'credentials.json' not found.")
    except SpreadsheetNotFound: sys.exit(f"Fatal: Google Sheet '{sheet_name}' not found.")
    except WorksheetNotFound: sys.exit("Fatal: 'Jobs' or 'Machines' worksheet missing.")
    except Exception as e: sys.exit(f"Unexpected error loading GSheet: {e}")

def load_data_from_excel(file_path: str) -> tuple[list[Machine], list[Job]]:
    """Loads machine and job data from an Excel file."""
    # ... (code for loading from Excel) ...
    try:
        machines_df = pd.read_excel(file_path, sheet_name='Machines')
        jobs_df = pd.read_excel(file_path, sheet_name='Jobs')
        machines = []
        for i, row in machines_df.iterrows():
            if 'machine_id' not in row: sys.exit("Error: 'machine_id' missing in 'Machines' sheet.")
            unavailable_periods = []
            if 'unavailable_periods' in row and pd.notna(row['unavailable_periods']):
                periods_str = str(row['unavailable_periods']).split(';')
                for period in periods_str:
                    if '-' not in period: sys.exit(f"Error in 'Machines' row {i+2}: Invalid 'unavailable_periods' format.")
                    start, end = map(int, period.split('-'))
                    unavailable_periods.append((start, end))
            machines.append(Machine(int(row['machine_id']), unavailable_periods))
        jobs = []
        for i, row in jobs_df.iterrows():
            for col in ['job_id', 'operations', 'due_date', 'priority']:
                if col not in row: sys.exit(f"Error: '{col}' missing in 'Jobs' sheet.")
            operations = []
            if 'operations' in row and pd.notna(row['operations']):
                ops_str = str(row['operations']).split(';')
                for op in ops_str:
                    if '(' not in op or ')' not in op: sys.exit(f"Error in 'Jobs' row {i+2}: Invalid 'operations' format.")
                    machine_id, proc_time = op.replace(')', '').split('(')
                    operations.append(Operation(int(machine_id), int(proc_time)))
            jobs.append(Job(int(row['job_id']), operations, int(row['due_date']), int(row['priority'])))
        return machines, jobs
    except FileNotFoundError: sys.exit(f"Fatal: Excel file '{file_path}' not found.")
    except ValueError as e: sys.exit(f"Missing sheet in Excel: {e}")
    except Exception as e: sys.exit(f"Unexpected error loading Excel: {e}")

def load_data_from_json(file_path: str) -> tuple[list[Machine], list[Job]]:
    """Loads machine and job data from a JSON file."""
    # ... (code for loading from JSON) ...
    with open(file_path, 'r') as f: data = json.load(f)
    machines = [Machine(m['machine_id'], [tuple(p) for p in m['unavailable_periods']]) for m in data['machines']]
    jobs = []
    for j_data in data['jobs']:
        ops = [Operation(o['machine_id'], o['processing_time']) for o in j_data['operations']]
        jobs.append(Job(j_data['job_id'], ops, j_data['due_date'], j_data['priority']))
    return machines, jobs