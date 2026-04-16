# models.py

class Operation:
    # ... (no changes here)
    def __init__(self, machine_id: int, processing_time: int):
        self.machine_id = machine_id
        self.processing_time = processing_time

    def __repr__(self):
        return f"Operation(Machine: {self.machine_id}, Time: {self.processing_time})"


class Job:
    # ... (no changes here)
    def __init__(self, job_id: int, operations: list[Operation], due_date: int, priority: int):
        self.job_id = job_id
        self.operations = operations
        self.due_date = due_date
        self.priority = priority

    def __repr__(self):
        return f"Job(ID: {self.job_id}, Prio: {self.priority}, Due: {self.due_date})"


class Machine:
    """Represents a machine on the shop floor with its own schedule."""
    # --- MODIFICATION FOR TODAY ---
    def __init__(self, machine_id: int, unavailable_periods: list[tuple[int, int]] = None):
        self.machine_id = machine_id
        self.available_at = 0
        self.last_job_id = None
        # A list of (start_time, end_time) tuples when the machine is down
        self.unavailable_periods = unavailable_periods if unavailable_periods else []

    def __repr__(self):
        return f"Machine(ID: {self.machine_id}, Last Job: {self.last_job_id})"
