# genetic_algorithm.py
import random
import copy

# --- MODIFIED FUNCTION SIGNATURE ---
# We now pass all parameters in, instead of using global constants.
def run_genetic_algorithm(jobs, machines, setup_time, pop_size, num_gen, mut_rate, tourn_size, w_makespan, w_tardiness):
    from main import schedule_fcfs # Local import to prevent circular dependency
    """The main function to run the Genetic Algorithm with multi-objective fitness."""
    
    population = create_initial_population(jobs, pop_size)
    best_overall_schedule = None
    best_overall_fitness = float('inf')

    print("\n--- Running Genetic Algorithm (Multi-Objective) ---")
    print(f"Settings: Pop={pop_size}, Gen={num_gen}, M-Rate={mut_rate}")
    print(f"Fitness Weights: Makespan={w_makespan}, Tardiness={w_tardiness}")
    
    for gen in range(num_gen):
        fitness_scores = []
        for chromosome in population:
            machine_copy = copy.deepcopy(machines)
            current_schedule = schedule_fcfs(chromosome, machine_copy, setup_time)
            
            # --- NEW FITNESS CALCULATION ---
            # 1. Calculate both objectives
            makespan = max(op[4] for op in current_schedule) if current_schedule else 0
            total_tardiness = calculate_tardiness(current_schedule, jobs)
            
            # 2. Calculate the combined, weighted fitness score
            fitness = (makespan * w_makespan) + (total_tardiness * w_tardiness)
            
            fitness_scores.append((chromosome, fitness, current_schedule, makespan, total_tardiness))

        # The rest of the GA works as before, but now uses the new combined fitness score
        best_in_gen = min(fitness_scores, key=lambda x: x[1])
        
        if best_in_gen[1] < best_overall_fitness:
            best_overall_fitness = best_in_gen[1]
            best_overall_schedule = best_in_gen[2]
            best_makespan = best_in_gen[3]
            best_tardiness = best_in_gen[4]
            print(f"Gen {gen+1}: New best! Fitness={best_overall_fitness:.2f} (Makespan={best_makespan}, Tardiness={best_tardiness})")

        # --- Elitism and Crossover ---
        next_generation = [best_in_gen[0]] # Keep the best individual
        
        while len(next_generation) < pop_size:
            parent1 = select_parents(fitness_scores, tourn_size)
            parent2 = select_parents(fitness_scores, tourn_size)
            child = crossover(parent1, parent2)
            child = mutate(child, mut_rate)
            next_generation.append(child)
        
        population = next_generation

    final_makespan = max(op[4] for op in best_overall_schedule) if best_overall_schedule else 0
    print(f"Genetic Algorithm finished. Best makespan: {final_makespan}")
    return best_overall_schedule

# --- NEW HELPER FUNCTION ---
# We copied this logic from the print_schedule function
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

# --- UNCHANGED FUNCTIONS BELOW (except for passing parameters) ---
def create_initial_population(jobs, size):
    population = []
    for _ in range(size):
        chromosome = random.sample(jobs, len(jobs))
        population.append(chromosome)
    return population

def select_parents(fitness_scores, tourn_size):
    tournament = random.sample(fitness_scores, tourn_size)
    winner = min(tournament, key=lambda x: x[1])
    return winner[0]

def crossover(parent1, parent2):
    child = [None] * len(parent1)
    start, end = sorted(random.sample(range(len(parent1)), 2))
    child[start:end] = parent1[start:end]
    parent2_jobs = [job for job in parent2 if job not in child]
    current_pos = 0
    for i in range(len(child)):
        if child[i] is None:
            child[i] = parent2_jobs[current_pos]
            current_pos += 1
    return child

def mutate(chromosome: list, mut_rate):
    if random.random() < mut_rate:
        idx1, idx2 = random.sample(range(len(chromosome)), 2)
        chromosome[idx1], chromosome[idx2] = chromosome[idx2], chromosome[idx1]
    return chromosome