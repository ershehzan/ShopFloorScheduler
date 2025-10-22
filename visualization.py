# visualization.py
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

def create_gantt_chart(schedule, title="Shop Floor Schedule"):
    """
    Creates and displays a Gantt chart for the given schedule.
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # A list of colors for different jobs
    colors = list(mcolors.TABLEAU_COLORS.values())
    
    # Y-axis will be the machines
    machine_ids = sorted(list(set(op[2] for op in schedule)))
    ax.set_yticks(machine_ids)
    ax.set_yticklabels([f'Machine {mid}' for mid in machine_ids])
    
    for op in schedule:
        job_id, op_index, machine_id, start_time, end_time = op
        duration = end_time - start_time
        color = colors[job_id % len(colors)]
        
        # Draw the bar for the operation
        ax.barh(machine_id, duration, left=start_time, height=0.6, 
                align='center', color=color, edgecolor='black')
        
        # Add text label (Job ID) in the middle of the bar
        ax.text(start_time + duration/2, machine_id, f'J{job_id}', 
                ha='center', va='center', color='white', fontweight='bold')

    ax.set_xlabel('Time')
    ax.set_ylabel('Machines')
    ax.set_title(title)
    ax.grid(True, which='both', linestyle='--', linewidth=0.5)
    
    # Invert y-axis to have Machine 0 at the top
    ax.invert_yaxis()
    
    plt.show()