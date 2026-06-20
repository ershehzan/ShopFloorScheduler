# data_loader.py
"""
Handles all data loading for the application.
Supports loading from Google Sheets, Excel, or JSON.

Raises ValueError or RuntimeError on data format issues instead of
calling sys.exit() so the FastAPI/Celery layer can catch and report
errors gracefully to the client.
"""
import pandas as pd
import openpyxl
import gspread
from gspread.exceptions import SpreadsheetNotFound, WorksheetNotFound
from models import Machine, Job, Operation
import json
from core.logger import logger


def _parse_unavailable_periods(row_value, row_index: int) -> list[tuple[int, int]]:
    """Parse a semicolon-delimited 'start-end' string into a list of period tuples."""
    periods = []
    if not row_value:
        return periods
    for period in str(row_value).split(';'):
        if '-' not in period:
            raise ValueError(
                f"Row {row_index}: Invalid 'unavailable_periods' format '{period}'. "
                "Expected 'start-end' (e.g. '10-20')."
            )
        start, end = map(int, period.split('-'))
        periods.append((start, end))
    return periods


def _parse_operations(ops_value, row_index: int) -> list[Operation]:
    """Parse a semicolon-delimited 'machine_id(proc_time)' string into Operation objects."""
    operations = []
    if not ops_value:
        return operations
    for op in str(ops_value).split(';'):
        op = op.strip()
        if '(' not in op or ')' not in op:
            raise ValueError(
                f"Row {row_index}: Invalid 'operations' format '{op}'. "
                "Expected 'machine_id(processing_time)' (e.g. '1(15)')."
            )
        machine_id_str, proc_time_str = op.replace(')', '').split('(')
        operations.append(Operation(int(machine_id_str.strip()), int(proc_time_str.strip())))
    return operations


def load_data_from_excel(file_path: str) -> tuple[list[Machine], list[Job]]:
    """
    Loads machine and job data from an Excel file.

    Expected sheets:
      - 'Machines': columns [machine_id, unavailable_periods (optional)]
      - 'Jobs':     columns [job_id, operations, due_date, priority]

    Args:
        file_path: Path to the .xlsx file.

    Returns:
        Tuple of (machines list, jobs list).

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If a required column or sheet is missing or data is malformed.
    """
    logger.info("Loading data from Excel: {}", file_path)

    try:
        machines_df = pd.read_excel(file_path, sheet_name='Machines')
        jobs_df = pd.read_excel(file_path, sheet_name='Jobs')
    except FileNotFoundError:
        logger.error("Excel file not found: {}", file_path)
        raise
    except ValueError as e:
        logger.error("Missing sheet in Excel file '{}': {}", file_path, str(e))
        raise

    # --- Parse Machines ---
    machines: list[Machine] = []
    for i, row in machines_df.iterrows():
        if 'machine_id' not in row:
            raise ValueError("Column 'machine_id' is missing from the 'Machines' sheet.")
        unavailable_periods = _parse_unavailable_periods(
            row.get('unavailable_periods') if pd.notna(row.get('unavailable_periods', None)) else None,
            row_index=i + 2,
        )
        machines.append(Machine(int(row['machine_id']), unavailable_periods))

    # --- Parse Jobs ---
    jobs: list[Job] = []
    for i, row in jobs_df.iterrows():
        for col in ['job_id', 'operations', 'due_date', 'priority']:
            if col not in row:
                raise ValueError(f"Column '{col}' is missing from the 'Jobs' sheet.")
        operations = _parse_operations(
            row['operations'] if pd.notna(row['operations']) else None,
            row_index=i + 2,
        )
        jobs.append(Job(int(row['job_id']), operations, int(row['due_date']), int(row['priority'])))

    logger.info("Excel loaded successfully: {} machines, {} jobs.", len(machines), len(jobs))
    return machines, jobs


def load_data_from_gsheet(sheet_name: str) -> tuple[list[Machine], list[Job]]:
    """
    Loads machine and job data from a Google Sheet.

    Requires a 'credentials.json' service account key file in the project root.
    The spreadsheet must have 'Machines' and 'Jobs' worksheets.
    """
    logger.info("Connecting to Google Sheet: {}", sheet_name)
    try:
        gc = gspread.service_account(filename='credentials.json')
        spreadsheet = gc.open(sheet_name)

        machines_df = pd.DataFrame(spreadsheet.worksheet("Machines").get_all_records())
        jobs_df = pd.DataFrame(spreadsheet.worksheet("Jobs").get_all_records())

        machines: list[Machine] = []
        for i, row in machines_df.iterrows():
            if 'machine_id' not in row:
                raise ValueError("Column 'machine_id' is missing from the 'Machines' sheet.")
            unavailable_periods = _parse_unavailable_periods(
                row.get('unavailable_periods') or None, row_index=i + 2
            )
            machines.append(Machine(int(row['machine_id']), unavailable_periods))

        jobs: list[Job] = []
        for i, row in jobs_df.iterrows():
            for col in ['job_id', 'operations', 'due_date', 'priority']:
                if col not in row:
                    raise ValueError(f"Column '{col}' is missing from the 'Jobs' sheet.")
            operations = _parse_operations(row.get('operations') or None, row_index=i + 2)
            jobs.append(Job(int(row['job_id']), operations, int(row['due_date']), int(row['priority'])))

        logger.info("Google Sheet loaded: {} machines, {} jobs.", len(machines), len(jobs))
        return machines, jobs

    except FileNotFoundError:
        logger.error("'credentials.json' not found.")
        raise
    except SpreadsheetNotFound:
        logger.error("Google Sheet '{}' not found.", sheet_name)
        raise
    except WorksheetNotFound:
        logger.error("'Jobs' or 'Machines' worksheet missing in '{}'.", sheet_name)
        raise
    except Exception as e:
        logger.error("Unexpected error loading Google Sheet: {}", str(e))
        raise


def load_data_from_json(file_path: str) -> tuple[list[Machine], list[Job]]:
    """
    Loads machine and job data from a JSON file.

    Expected structure:
        {
          "machines": [{"machine_id": 1, "unavailable_periods": [[10, 20]]}],
          "jobs": [{"job_id": 1, "due_date": 100, "priority": 2,
                    "operations": [{"machine_id": 1, "processing_time": 15}]}]
        }
    """
    logger.info("Loading data from JSON: {}", file_path)
    with open(file_path, 'r') as f:
        data = json.load(f)

    machines = [
        Machine(m['machine_id'], [tuple(p) for p in m.get('unavailable_periods', [])])
        for m in data['machines']
    ]
    jobs = [
        Job(
            j['job_id'],
            [Operation(o['machine_id'], o['processing_time']) for o in j['operations']],
            j['due_date'],
            j['priority'],
        )
        for j in data['jobs']
    ]

    logger.info("JSON loaded: {} machines, {} jobs.", len(machines), len(jobs))
    return machines, jobs
