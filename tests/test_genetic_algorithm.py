# tests/test_genetic_algorithm.py
"""
Tests for genetic_algorithm.py — GA components and end-to-end run.
"""
import copy
import pytest
from models import Job, Operation, Machine
from genetic_algorithm import (
    create_initial_population,
    select_parents,
    crossover,
    mutate,
    calculate_tardiness,
    run_genetic_algorithm,
)


class TestInitialPopulation:
    def test_population_size(self, sample_jobs):
        pop = create_initial_population(sample_jobs, size=20)
        assert len(pop) == 20

    def test_chromosomes_are_permutations(self, sample_jobs):
        """Each chromosome should contain all jobs exactly once."""
        pop = create_initial_population(sample_jobs, size=10)
        job_ids = sorted(j.job_id for j in sample_jobs)
        for chromosome in pop:
            assert sorted(j.job_id for j in chromosome) == job_ids

    def test_population_diversity(self, sample_jobs):
        """At least some chromosomes should differ (random permutations)."""
        pop = create_initial_population(sample_jobs, size=50)
        orderings = set()
        for chromosome in pop:
            orderings.add(tuple(j.job_id for j in chromosome))
        # With 5 jobs and 50 samples, we expect more than 1 unique ordering
        assert len(orderings) > 1


class TestCrossover:
    def test_preserves_all_jobs(self, sample_jobs):
        """OX1 crossover child should contain all jobs with no duplicates."""
        import random
        random.seed(42)
        parent1 = list(sample_jobs)
        parent2 = list(reversed(sample_jobs))
        child = crossover(parent1, parent2)

        assert len(child) == len(sample_jobs)
        child_ids = sorted(j.job_id for j in child)
        expected_ids = sorted(j.job_id for j in sample_jobs)
        assert child_ids == expected_ids

    def test_returns_list(self, sample_jobs):
        child = crossover(list(sample_jobs), list(reversed(sample_jobs)))
        assert isinstance(child, list)


class TestMutation:
    def test_preserves_length(self, sample_jobs):
        """Mutation should not change chromosome length."""
        chromosome = list(sample_jobs)
        mutated = mutate(chromosome, mut_rate=1.0)  # force mutation
        assert len(mutated) == len(sample_jobs)

    def test_preserves_all_jobs(self, sample_jobs):
        """Mutation should keep all jobs (just swap two)."""
        import random
        random.seed(42)
        chromosome = list(sample_jobs)
        mutated = mutate(chromosome, mut_rate=1.0)
        assert sorted(j.job_id for j in mutated) == sorted(j.job_id for j in sample_jobs)

    def test_no_mutation_at_zero_rate(self, sample_jobs):
        """With 0 mutation rate, chromosome should be unchanged."""
        chromosome = list(sample_jobs)
        original_order = [j.job_id for j in chromosome]
        mutated = mutate(chromosome, mut_rate=0.0)
        assert [j.job_id for j in mutated] == original_order


class TestTournamentSelection:
    def test_returns_chromosome(self, sample_jobs, fresh_machines):
        """Tournament selection should return a valid chromosome."""
        from scheduler.engine import schedule_fcfs

        fitness_scores = []
        for chromosome in create_initial_population(sample_jobs, size=10):
            machines_copy = copy.deepcopy(fresh_machines)
            sched = schedule_fcfs(chromosome, machines_copy, setup_time=2)
            makespan = max(op[4] for op in sched) if sched else 0
            fitness_scores.append((chromosome, makespan, sched, makespan, 0))

        winner = select_parents(fitness_scores, tourn_size=3)
        assert isinstance(winner, list)
        assert len(winner) == len(sample_jobs)


class TestCalculateTardiness:
    def test_matches_metrics_module(self, sample_jobs, fresh_machines):
        """GA's calculate_tardiness should match scheduler.metrics version."""
        from scheduler.engine import schedule_fcfs
        from scheduler.metrics import calculate_tardiness as metrics_tardiness

        sched = schedule_fcfs(sample_jobs, fresh_machines, setup_time=2)
        ga_result = calculate_tardiness(sched, sample_jobs)
        metrics_result = metrics_tardiness(sched, sample_jobs)
        assert ga_result == metrics_result


class TestGAEndToEnd:
    def test_returns_valid_schedule(self, sample_jobs, fresh_machines):
        """Full GA run should return a non-empty list of schedule tuples."""
        schedule = run_genetic_algorithm(
            jobs=sample_jobs,
            machines=fresh_machines,
            setup_time=2,
            pop_size=10,
            num_gen=5,
            mut_rate=0.1,
            tourn_size=3,
            w_makespan=0.6,
            w_tardiness=0.4,
        )
        assert schedule is not None
        assert len(schedule) > 0
        # Each entry should be a 5-tuple
        for op in schedule:
            assert len(op) == 5
            assert op[4] > op[3], "end_time must be > start_time"

    def test_covers_all_operations(self, sample_jobs, fresh_machines):
        """GA schedule should contain all operations from all jobs."""
        total_ops = sum(len(j.operations) for j in sample_jobs)
        schedule = run_genetic_algorithm(
            jobs=sample_jobs,
            machines=fresh_machines,
            setup_time=2,
            pop_size=10,
            num_gen=5,
            mut_rate=0.1,
            tourn_size=3,
            w_makespan=0.6,
            w_tardiness=0.4,
        )
        assert len(schedule) == total_ops
