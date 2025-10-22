# visualization.py
"""
Contains the function to generate a Gantt chart for a given schedule.
Uses the matplotlib library for plotting.
"""
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

def create_gantt_chart(schedule, title="Shop Floor Schedule"):
    """
    Creates and displays a Gantt chart for the given schedule.
    
    Args:
        schedule (list): The schedule data (list of tuples).
        title (str): The title for the chart.
    """
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Get a list of unique machine IDs and job IDs from the schedule
    machine_ids = sorted(list(set(op[2] for op in schedule)))
    job_ids = sorted(list(set(op[0] for op in schedule)))
    
    # Create a color mapping for jobs
    colors = plt.cm.get_cmap('tab20', len(job_ids))
    color_map = {job_id: colors(i) for i, job_id in enumerate(job_ids)}
    
    # Set Y-axis labels to be "Machine 0", "Machine 1", etc.
    ax.set_yticks(machine_ids)
    ax.set_yticklabels([f'Machine {mid}' for mid in machine_ids])
    
    # Plot each operation as a horizontal bar
    for op in schedule:
        job_id, op_index, machine_id, start_time, end_time = op
        duration = end_time - start_time
        color = color_map[job_id]
        
        ax.barh(machine_id, duration, left=start_time, height=0.6, 
                align='center', color=color, edgecolor='black', alpha=0.8)
        
        # Add text label (Job ID) in the middle of the bar
        ax.text(start_time + duration/2, machine_id, f'J{job_id}', 
                ha='center', va='center', color='white', fontweight='bold')

    ax.set_xlabel('Time Units')
    ax.set_ylabel('Machines')
    ax.set_title(title)
    ax.grid(True, which='major', axis='x', linestyle='--', linewidth=0.5)
    
    # Invert y-axis to have Machine 0 at the top
    ax.invert_yaxis()
    plt.tight_layout()
    plt.show()