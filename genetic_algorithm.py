 # genetic_algorithm.py
"""
Contains all logic for the multi-objective Genetic Algorithm (GA).

This module implements the core GA loop:
1.  Population Initialization
2.  Fitness Evaluation (Multi-Objective)
3.  Selection (Tournament)
4.  Crossover (Ordered)
5.  Mutation (Swap)
"""
import random
import copy

def run_genetic_algorithm(jobs, machines, setup_time, pop_size, num_gen, mut_rate, tourn_size, w_makespan, w_tardiness):
    """
    Runs the complete Genetic Algorithm to find a near-optimal schedule.
    
    Args:
        jobs (list[Job]): The list of jobs to schedule.
        machines (list[Machine]): The list of available machines.
        setup_time (int): The time required for machine setup.
        pop_size (int): The number of individuals in each generation.
        num_gen (int): The number of generations to evolve.
        mut_rate (float): The probability (0.0 - 1.0) of a mutation.
        tourn_size (int): The number of individuals in a selection tournament.
        w_makespan (float): The weight for the makespan objective.
        w_tardiness (float): The weight for the tardiness objective.
        
    Returns:
        list: The best schedule found by the algorithm.
    """
    from main import schedule_fcfs # Local import to prevent circular dependency
    
    population = create_initial_population(jobs, pop_size)
    best_overall_schedule = None
    best_overall_fitness = float('inf')

    print("\n--- Running Genetic Algorithm (Multi-Objective) ---")
    print(f"Settings: Pop={pop_size}, Gen={num_gen}, M-Rate={mut_rate}")
    print(f"Fitness Weights: Makespan={w_makespan}, Tardiness={w_tardiness}")
    
    # Start the evolution loop
    for gen in range(num_gen):
        fitness_scores = []
        
        # 1. Calculate fitness for each individual in the population
        for chromosome in population:
            machine_copy = copy.deepcopy(machines)
            # Use the main scheduler as the fitness function
            current_schedule = schedule_fcfs(chromosome, machine_copy, setup_time)
            
            # --- Multi-Objective Fitness Calculation ---
            makespan = max(op[4] for op in current_schedule) if current_schedule else 0
            total_tardiness = calculate_tardiness(current_schedule, jobs)
            
            # Combine objectives into a single fitness score
            fitness = (makespan * w_makespan) + (total_tardiness * w_tardiness)
            
            fitness_scores.append((chromosome, fitness, current_schedule, makespan, total_tardiness))

        # Find the best individual in this generation
        best_in_gen = min(fitness_scores, key=lambda x: x[1])
        
        # Update the all-time best if this one is better
        if best_in_gen[1] < best_overall_fitness:
            best_overall_fitness = best_in_gen[1]
            best_overall_schedule = best_in_gen[2]
            best_makespan = best_in_gen[3]
            best_tardiness = best_in_gen[4]
            print(f"Gen {gen+1}: New best! Fitness={best_overall_fitness:.2f} (Makespan={best_makespan}, Tardiness={best_tardiness})")

        # 2. Create the next generation
        next_generation = [best_in_gen[0]] # Elitism: Keep the best individual
        
        # 3. Fill the rest of the generation with new children
        while len(next_generation) < pop_size:
            # 3a. Selection
            parent1 = select_parents(fitness_scores, tourn_size)
            parent2 = select_parents(fitness_scores, tourn_size)
            
            # 3b. Crossover
            child = crossover(parent1, parent2)
            
            # 3c. Mutation
            child = mutate(child, mut_rate)
            
            next_generation.append(child)
        
        population = next_generation

    final_makespan = max(op[4] for op in best_overall_schedule) if best_overall_schedule else 0
    print(f"Genetic Algorithm finished. Best makespan: {final_makespan}")
    return best_overall_schedule

def calculate_tardiness(schedule: list, jobs: list) -> int:
    """Calculates the total tardiness for a given schedule."""
    job_completion_times = {}
    for scheduled_op in schedule:
        job_id, end_time = scheduled_op[0], scheduled_op[4]
        job_completion_times[job_id] = max(job_completion_times.get(job_id, 0), end_time)

    job_map = {job.job_id: job for job in jobs}
    total_tardiness = 0
    for job_id, completion_time in job_completion_times.items():
        if job_id in job_map:
            job = job_map[job_id]
            tardiness = max(0, completion_time - job.due_date)
            total_tardiness += tardiness
    return total_tardiness

def create_initial_population(jobs, size):
    """Creates an initial population of random schedules."""
    population = []
    for _ in range(size):
        chromosome = random.sample(jobs, len(jobs)) # A random permutation of jobs
        population.append(chromosome)
    return population

def select_parents(fitness_scores, tourn_size):
    """Selects one parent using tournament selection."""
    tournament = random.sample(fitness_scores, tourn_size)
    winner = min(tournament, key=lambda x: x[1]) # [1] is the fitness score
    return winner[0] # [0] is the chromosome

def crossover(parent1, parent2):
    """Creates a new child schedule using Ordered Crossover (OX1)."""
    child = [None] * len(parent1)
    start, end = sorted(random.sample(range(len(parent1)), 2))
    
    # Copy the slice from parent 1
    child[start:end] = parent1[start:end]
    
    # Get the remaining jobs from parent 2
    parent2_jobs = [job for job in parent2 if job not in child]
    
    # Fill the Nones in the child
    current_pos = 0
    for i in range(len(child)):
        if child[i] is None:
            child[i] = parent2_jobs[current_pos]
            current_pos += 1
    return child

def mutate(chromosome: list, mut_rate):
    """Applies swap mutation to a chromosome."""
    if random.random() < mut_rate:
        idx1, idx2 = random.sample(range(len(chromosome)), 2)
        chromosome[idx1], chromosome[idx2] = chromosome[idx2], chromosome[idx1] # Swap
    return chromosome
