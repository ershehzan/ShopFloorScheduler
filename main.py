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
from data_loader import load_data_from_excel
from exporter import export_to_excel
from genetic_algorithm import run_genetic_algorithm
from scheduler.engine import schedule_fcfs, schedule_spt, schedule_edd, schedule_wspt
from scheduler.metrics import build_full_metrics
from core.logger import logger
import copy
import os
import configparser

# --- OUTPUT FUNCTION ---
def print_schedule(schedule, jobs, title="Schedule"):
    """Prints a formatted summary of the schedule's performance to the console."""
    logger.info("=== {} ===", title)
    logger.info("Job | Prio | Due Date | Completion | Tardiness")
    
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
            logger.info("{:<4}| {:<5}| {:<9}| {:<11}| {:<9}", job_id, job.priority, job.due_date, completion_time, tardiness)

    makespan = max(op[4] for op in schedule) if schedule else 0
    logger.info("Makespan (Total Time): {}", makespan)
    logger.info("Total Tardiness: {}", total_tardiness)

# --- MAIN EXECUTION BLOCK ---
if __name__ == "__main__":
    
    # --- 1. Load Configuration ---
    config = configparser.ConfigParser()
    if not os.path.exists('config.ini'):
        logger.warning("'config.ini' not found. Using default settings.")
        SETUP_TIME = 2
        OUTPUT_FOLDER = 'output'
        GA_POP_SIZE, GA_NUM_GEN, GA_MUT_RATE, GA_TOURN_SIZE = 30, 50, 0.1, 3
        GA_W_MAKESPAN, GA_W_TARDINESS = 0.6, 0.4
    else:
        logger.info("Reading configuration from config.ini...")
        config.read('config.ini')
        
        # Read settings with error handling and defaults
        try: SETUP_TIME = config.getint('Settings', 'setup_time')
        except: SETUP_TIME = 2; logger.warning("'setup_time' missing in config. Using default: 2")
        
        try: OUTPUT_FOLDER = config.get('Paths', 'output_folder')
        except: OUTPUT_FOLDER = 'output'; logger.warning("'output_folder' missing in config. Using default: 'output'")

        try: GA_POP_SIZE = config.getint('GeneticAlgorithm', 'population_size')
        except: GA_POP_SIZE = 30; logger.warning("'population_size' missing in config. Using default: 30")

        try: GA_NUM_GEN = config.getint('GeneticAlgorithm', 'num_generations')
        except: GA_NUM_GEN = 50; logger.warning("'num_generations' missing in config. Using default: 50")

        try: GA_MUT_RATE = config.getfloat('GeneticAlgorithm', 'mutation_rate')
        except: GA_MUT_RATE = 0.1; logger.warning("'mutation_rate' missing in config. Using default: 0.1")

        try: GA_TOURN_SIZE = config.getint('GeneticAlgorithm', 'tournament_size')
        except: GA_TOURN_SIZE = 3; logger.warning("'tournament_size' missing in config. Using default: 3")

        try: GA_W_MAKESPAN = config.getfloat('GeneticAlgorithm', 'makespan_weight')
        except: GA_W_MAKESPAN = 0.6; logger.warning("'makespan_weight' missing in config. Using default: 0.6")

        try: GA_W_TARDINESS = config.getfloat('GeneticAlgorithm', 'tardiness_weight')
        except: GA_W_TARDINESS = 0.4; logger.warning("'tardiness_weight' missing in config. Using default: 0.4")

    # --- 2. Load Data ---
    logger.info("Loading data from data.xlsx...")
    machines, jobs_data = load_data_from_excel('data.xlsx')
    
    # --- 3. Run Simple Schedulers ---
    simple_schedulers = { 
        "FCFS": schedule_fcfs, 
        "SPT": schedule_spt, 
        "EDD": schedule_edd, 
        "WSPT": schedule_wspt
    }
    
    logger.info("Running Simple Schedulers (Setup Time: {})", SETUP_TIME)
    
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

    logger.info("All schedules have been exported to the '{}' folder.", OUTPUT_FOLDER)
    logger.info("All schedules exported to '{}' folder.", OUTPUT_FOLDER)
