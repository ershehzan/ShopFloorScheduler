# main.py
from models import Job, Operation, Machine
from visualization import create_gantt_chart
from data_loader import load_data_from_gsheet
from exporter import export_to_excel
import copy
import os
import configparser
from genetic_algorithm import run_genetic_algorithm

# ... (All schedule functions: schedule_fcfs, spt, edd, wspt, are UNCHANGED) ...
def schedule_fcfs(jobs: list[Job], machines: list[Machine], setup_time: int):
    # ... (no change)
    schedule = []
    machine_map = {m.machine_id: m for m in machines}
    for job in jobs:
        current_job_end_time = 0
        for i, operation in enumerate(job.operations):
            machine = machine_map[operation.machine_id]
            setup_needed = machine.last_job_id is not None and machine.last_job_id != job.job_id
            setup = setup_time if setup_needed else 0
            earliest_start = max(machine.available_at + setup, current_job_end_time)
            valid_start_time = earliest_start
            while True:
                conflict_found = False
                proposed_end_time = valid_start_time + operation.processing_time
                for unavailable_start, unavailable_end in machine.unavailable_periods:
                    if valid_start_time < unavailable_end and unavailable_start < proposed_end_time:
                        valid_start_time = unavailable_end
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

def schedule_spt(jobs: list[Job], machines: list[Machine], setup_time: int):
    # ... (no change)
    sorted_jobs = sorted(jobs, key=lambda job: sum(op.processing_time for op in job.operations))
    return schedule_fcfs(sorted_jobs, machines, setup_time)

def schedule_edd(jobs: list[Job], machines: list[Machine], setup_time: int):
    # ... (no change)
    sorted_jobs = sorted(jobs, key=lambda job: job.due_date)
    return schedule_fcfs(sorted_jobs, machines, setup_time)

def schedule_wspt(jobs: list[Job], machines: list[Machine], setup_time: int):
    # ... (no change)
    sorted_jobs = sorted(jobs, key=lambda job: sum(op.processing_time for op in job.operations) / job.priority)
    return schedule_fcfs(sorted_jobs, machines, setup_time)

def print_schedule(schedule, jobs, title="Schedule"):
    # ... (This function is unchanged)
    print(f"\n--- {title} ---")
    print("Job | Prio | Due Date | Completion | Tardiness")
    print("----------------------------------------------------")
    
    job_completion_times = {}
    for scheduled_op in schedule:
        job_id, end_time = scheduled_op[0], scheduled_op[4]
        job_completion_times[job_id] = max(job_completion_times.get(job_id, 0), end_time)

    job_map = {job.job_id: job for job in jobs}
    total_tardiness = 0
    
    # Sort jobs by completion time for logical output
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


# main.py

# ... (all other functions: schedule_fcfs, schedule_spt, schedule_edd,
# ...  schedule_wspt, and print_schedule remain UNCHANGED) ...


if __name__ == "__main__":
    # --- MODIFIED BLOCK FOR TODAY ---
    
    config = configparser.ConfigParser()
    
    # Check if the config file exists first
    if not os.path.exists('config.ini'):
        print("--- WARNING: 'config.ini' not found. ---")
        print("Using default settings for the simulation.")
        # Set all default values manually
        SETUP_TIME = 2
        OUTPUT_FOLDER = 'output'
        GA_POP_SIZE = 30
        GA_NUM_GEN = 50
        GA_MUT_RATE = 0.1
        GA_TOURN_SIZE = 3
        GA_W_MAKESPAN = 0.6
        GA_W_TARDINESS = 0.4
    else:
        print("Reading configuration from config.ini...")
        config.read('config.ini')
        
        # Read settings with error handling for each value
        try:
            SETUP_TIME = config.getint('Settings', 'setup_time')
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            print("Warning: 'setup_time' missing or invalid in config.ini. Using default: 2")
            SETUP_TIME = 2
            
        try:
            OUTPUT_FOLDER = config.get('Paths', 'output_folder')
        except (configparser.NoSectionError, configparser.NoOptionError):
            print("Warning: 'output_folder' missing in config.ini. Using default: 'output'")
            OUTPUT_FOLDER = 'output'

        # Read Genetic Algorithm settings
        try:
            GA_POP_SIZE = config.getint('GeneticAlgorithm', 'population_size')
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            print("Warning: 'population_size' missing or invalid. Using default: 30")
            GA_POP_SIZE = 30

        try:
            GA_NUM_GEN = config.getint('GeneticAlgorithm', 'num_generations')
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            print("Warning: 'num_generations' missing or invalid. Using default: 50")
            GA_NUM_GEN = 50

        try:
            GA_MUT_RATE = config.getfloat('GeneticAlgorithm', 'mutation_rate')
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            print("Warning: 'mutation_rate' missing or invalid. Using default: 0.1")
            GA_MUT_RATE = 0.1

        try:
            GA_TOURN_SIZE = config.getint('GeneticAlgorithm', 'tournament_size')
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            print("Warning: 'tournament_size' missing or invalid. Using default: 3")
            GA_TOURN_SIZE = 3

        try:
            GA_W_MAKESPAN = config.getfloat('GeneticAlgorithm', 'makespan_weight')
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            print("Warning: 'makespan_weight' missing or invalid. Using default: 0.6")
            GA_W_MAKESPAN = 0.6

        try:
            GA_W_TARDINESS = config.getfloat('GeneticAlgorithm', 'tardiness_weight')
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            print("Warning: 'tardiness_weight' missing or invalid. Using default: 0.4")
            GA_W_TARDINESS = 0.4

    # --- This part below is unchanged, it just uses the values from above ---
    machines, jobs_data = load_data_from_gsheet('ShopFloorData')
    
    simple_schedulers = { 
        "FCFS": schedule_fcfs, 
        "SPT": schedule_spt, 
        "EDD": schedule_edd, 
        "WSPT": schedule_wspt
    }
    
    print(f"--- Running Simple Schedulers (Setup Time: {SETUP_TIME}) ---")
    
    for name, func in simple_schedulers.items():
        machine_copy = copy.deepcopy(machines)
        schedule_result = func(jobs_data, machine_copy, SETUP_TIME)
        print_schedule(schedule_result, jobs_data, f"{name} Schedule")
        create_gantt_chart(schedule_result, f"{name} Schedule")
        output_filename = os.path.join(OUTPUT_FOLDER, f'{name}_schedule.xlsx')
        export_to_excel(schedule_result, jobs_data, output_filename)
        
    ga_schedule = run_genetic_algorithm(
        jobs_data, 
        copy.deepcopy(machines), 
        SETUP_TIME,
        GA_POP_SIZE,
        GA_NUM_GEN,
        GA_MUT_RATE,
        GA_TOURN_SIZE,
        GA_W_MAKESPAN,
        GA_W_TARDINESS
    )
    
    print_schedule(ga_schedule, jobs_data, "Genetic Algorithm Schedule")
    create_gantt_chart(ga_schedule, "Genetic Algorithm Schedule")
    output_filename = os.path.join(OUTPUT_FOLDER, 'GA_schedule.xlsx')
    export_to_excel(ga_schedule, jobs_data, output_filename)

    print(f"\n✅ All schedules have been exported to the '{OUTPUT_FOLDER}' folder.")