# exporter.py
import pandas as pd
import os

def export_to_excel(schedule: list, jobs: list, file_path: str):
    """
    Exports the final schedule and performance metrics to an Excel file.
    """
    # --- Create the main schedule DataFrame ---
    schedule_df = pd.DataFrame(schedule, columns=[
        'Job ID', 'Operation Index', 'Machine ID', 'Start Time', 'End Time'
    ])

    # --- Create the summary/metrics DataFrame ---
    job_completion_times = {}
    for scheduled_op in schedule:
        job_id, end_time = scheduled_op[0], scheduled_op[4]
        job_completion_times[job_id] = max(job_completion_times.get(job_id, 0), end_time)

    job_map = {job.job_id: job for job in jobs}
    summary_data = []
    total_tardiness = 0
    for job_id, completion_time in sorted(job_completion_times.items()):
        job = job_map[job_id]
        tardiness = max(0, completion_time - job.due_date)
        total_tardiness += tardiness
        summary_data.append([job_id, job.priority, job.due_date, completion_time, tardiness])
    
    summary_df = pd.DataFrame(summary_data, columns=[
        'Job ID', 'Priority', 'Due Date', 'Completion Time', 'Tardiness'
    ])
    
    # Calculate Makespan
    makespan = max(op[4] for op in schedule) if schedule else 0

    # --- Write to an Excel file with two sheets ---
    # Ensure the output directory exists
    output_dir = os.path.dirname(file_path)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
        schedule_df.to_excel(writer, sheet_name='Full_Schedule', index=False)
        summary_df.to_excel(writer, sheet_name='Performance_Metrics', index=False)
        
        # Add makespan and total tardiness to the metrics sheet
        workbook = writer.book
        metrics_sheet = writer.sheets['Performance_Metrics']
        metrics_sheet.cell(row=len(summary_df) + 3, column=1, value='Makespan (Total Time)')
        metrics_sheet.cell(row=len(summary_df) + 3, column=2, value=makespan)
        metrics_sheet.cell(row=len(summary_df) + 4, column=1, value='Total Tardiness')
        metrics_sheet.cell(row=len(summary_df) + 4, column=2, value=total_tardiness)