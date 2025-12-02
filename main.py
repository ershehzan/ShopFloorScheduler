# main.py
"""
The main entry point for the Shop Floor Scheduler application.

This script performs the following steps:
1.  Loads configuration from `config.ini` with error handling.
2.  Loads data from the specified source (Excel or Google Sheets).
3.  Runs all scheduling algorithms (simple heuristics + Genetic Algorithm).
4.  For each result, it:
    - Prints a performance summary to the console.
    - Generates and displays a Gantt chart.
    - Exports a detailed Excel report to the `output/` folder.
"""
from models import Job, Operation, Machine
from visualization import create_gantt_chart
# --- CHANGE 1: Import the correct function ---
from data_loader import load_data_from_excel
from exporter import export_to_excel
from genetic_algorithm import run_genetic_algorithm
import copy
import os
import configparser

# --- CORE SCHEDULING ENGINE ---
def schedule_fcfs(jobs: list[Job], machines: list[Machine], setup_time: int) -> list:
    """
    Schedules jobs using the First-Come, First-Served (FCFS) algorithm.
    This is the core scheduling engine that also handles all constraints.
    """
    schedule = []
    machine_map = {m.machine_id: m for m in machines}

    for job in jobs:
        current_job_end_time = 0
        for i, operation in enumerate(job.operations):
            machine = machine_map[operation.machine_id]
            
            setup = 0
            if machine.last_job_id is not None and machine.last_job_id != job.job_id:
                setup = setup_time
            
            earliest_start = max(machine.available_at + setup, current_job_end_time)

            valid_start_time = earliest_start
            while True:
                conflict_found = False
                proposed_end_time = valid_start_time + operation.processing_time
                for down_start, down_end in machine.unavailable_periods:
                    if valid_start_time < down_end and down_start < proposed_end_time:
                        valid_start_time = down_end
                        conflict_found = True
                        break
                if not conflict_found:
                    break
            
            start_time = valid_start_time
            end_time = start_time + operation.processing_time
            
            schedule.append((job.job_id, i, machine.machine_id, start_time, end_time))
            
            machine.available_at = end_time
            machine.last_job_id = job.job_id
            current_job_end_time = end_time
            
    return schedule

# --- SIMPLE HEURISTICS ---
def schedule_spt(jobs: list[Job], machines: list[Machine], setup_time: int) -> list:
    """Schedules jobs using Shortest Processing Time (SPT) rule."""
    sorted_jobs = sorted(jobs, key=lambda job: sum(op.processing_time for op in job.operations))
    return schedule_fcfs(sorted_jobs, machines, setup_time)

def schedule_edd(jobs: list[Job], machines: list[Machine], setup_time: int) -> list:
    """Schedules jobs using Earliest Due Date (EDD) rule."""
    sorted_jobs = sorted(jobs, key=lambda job: job.due_date)
    return schedule_fcfs(sorted_jobs, machines, setup_time)

def schedule_wspt(jobs: list[Job], machines: list[Machine], setup_time: int) -> list:
    """Schedules jobs using Weighted Shortest Processing Time (WSPT) rule."""
    sorted_jobs = sorted(jobs, key=lambda job: sum(op.processing_time for op in job.operations) / job.priority)
    return schedule_fcfs(sorted_jobs, machines, setup_time)

# --- OUTPUT FUNCTION ---
def print_schedule(schedule, jobs, title="Schedule"):
    """Prints a formatted summary of the schedule's performance to the console."""
    print(f"\n--- {title} ---")
    print("Job | Prio | Due Date | Completion | Tardiness")
    print("----------------------------------------------------")
    
    job_completion_times = {}
    for scheduled_op in schedule:
        job_id, end_time = scheduled_op[0], scheduled_op[4]
        job_completion_times[job_id] = max(job_completion_times.get(job_id, 0), end_time)

    job_map = {job.job_id: job for job in jobs}
    total_tardiness = 0
    
    sorted_job_ids = sorted(job_completion_times.keys(), key=lambda j_id: job_completion_times[j_id])

    for job_id in sorted_job_ids:
        if job_id in job_map:
            job = job_map[job_id]
            completion_time = job_completion_times[job_id]
            tardiness = max(0, completion_time - job.due_date)
            total_tardiness += tardiness
            print(f"{job_id:<4}| {job.priority:<5}| {job.due_date:<9}| {completion_time:<11}| {tardiness:<9}")

    makespan = max(op[4] for op in schedule) if schedule else 0
    print("----------------------------------------------------")
    print(f"Makespan (Total Time): {makespan}")
    print(f"Total Tardiness: {total_tardiness}")

# --- MAIN EXECUTION BLOCK ---
if __name__ == "__main__":
    
    # --- 1. Load Configuration ---
    config = configparser.ConfigParser()
    if not os.path.exists('config.ini'):
        print("--- WARNING: 'config.ini' not found. Using default settings. ---")
        SETUP_TIME = 2
        OUTPUT_FOLDER = 'output'
        GA_POP_SIZE, GA_NUM_GEN, GA_MUT_RATE, GA_TOURN_SIZE = 30, 50, 0.1, 3
        GA_W_MAKESPAN, GA_W_TARDINESS = 0.6, 0.4
    else:
        print("Reading configuration from config.ini...")
        config.read('config.ini')
        
        # Read settings with error handling and defaults
        try: SETUP_TIME = config.getint('Settings', 'setup_time')
        except: SETUP_TIME = 2; print("Warning: 'setup_time' missing. Using default: 2")
        
        try: OUTPUT_FOLDER = config.get('Paths', 'output_folder')
        except: OUTPUT_FOLDER = 'output'; print("Warning: 'output_folder' missing. Using default: 'output'")

        try: GA_POP_SIZE = config.getint('GeneticAlgorithm', 'population_size')
        except: GA_POP_SIZE = 30; print("Warning: 'population_size' missing. Using default: 30")

        try: GA_NUM_GEN = config.getint('GeneticAlgorithm', 'num_generations')
        except: GA_NUM_GEN = 50; print("Warning: 'num_generations' missing. Using default: 50")

        try: GA_MUT_RATE = config.getfloat('GeneticAlgorithm', 'mutation_rate')
        except: GA_MUT_RATE = 0.1; print("Warning: 'mutation_rate' missing. Using default: 0.1")

        try: GA_TOURN_SIZE = config.getint('GeneticAlgorithm', 'tournament_size')
        except: GA_TOURN_SIZE = 3; print("Warning: 'tournament_size' missing. Using default: 3")

        try: GA_W_MAKESPAN = config.getfloat('GeneticAlgorithm', 'makespan_weight')
        except: GA_W_MAKESPAN = 0.6; print("Warning: 'makespan_weight' missing. Using default: 0.6")

        try: GA_W_TARDINESS = config.getfloat('GeneticAlgorithm', 'tardiness_weight')
        except: GA_W_TARDINESS = 0.4; print("Warning: 'tardiness_weight' missing. Using default: 0.4")

    # --- 2. Load Data ---
    # --- CHANGE 2: Call the Excel function ---
    print("Loading data from data.xlsx...")
    machines, jobs_data = load_data_from_excel('data.xlsx')
    
    # --- 3. Run Simple Schedulers ---
    simple_schedulers = { 
        "FCFS": schedule_fcfs, 
        "SPT": schedule_spt, 
        "EDD": schedule_edd, 
        "WSPT": schedule_wspt
    }
    
    print(f"--- Running Simple Schedulers (Setup Time: {SETUP_TIME}) ---")
    
    for name, func in simple_schedulers.items():
        machine_copy = copy.deepcopy(machines) # Deepcopy ensures each algo gets fresh machines
        schedule_result = func(jobs_data, machine_copy, SETUP_TIME)
        
        print_schedule(schedule_result, jobs_data, f"{name} Schedule")
        create_gantt_chart(schedule_result, f"{name} Schedule")
        
        output_filename = os.path.join(OUTPUT_FOLDER, f'{name}_schedule.xlsx')
        export_to_excel(schedule_result, jobs_data, output_filename)
        
    # --- 4. Run the Genetic Algorithm ---
    ga_schedule = run_genetic_algorithm(
        jobs_data, copy.deepcopy(machines), SETUP_TIME,
        GA_POP_SIZE, GA_NUM_GEN, GA_MUT_RATE, GA_TOURN_SIZE,
        GA_W_MAKESPAN, GA_W_TARDINESS
    )
    
    print_schedule(ga_schedule, jobs_data, "Genetic Algorithm Schedule")
    create_gantt_chart(ga_schedule, "Genetic Algorithm Schedule")
    output_filename = os.path.join(OUTPUT_FOLDER, 'GA_schedule.xlsx')
    export_to_excel(ga_schedule, jobs_data, output_filename)

    print(f"\n✅ All schedules have been exported to the '{OUTPUT_FOLDER}' folder.")
