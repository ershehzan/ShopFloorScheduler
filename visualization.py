# visualization.py
"""
Contains the function to generate a Gantt chart for a given schedule.
Uses the matplotlib library for plotting.
"""
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np

def create_gantt_chart(schedule, title="Shop Floor Schedule"):
    """
    Creates and displays a visually appealing and readable Gantt chart 
    for the given schedule.
    
    Args:
        schedule (list): The schedule data (list of tuples: 
                         (job_id, op_index, machine_id, start_time, end_time)).
        title (str): The title for the chart.
    """
    if not schedule:
        print(f"No schedule data to create Gantt chart for: {title}")
        return

    fig, ax = plt.subplots(figsize=(15, 8)) # Increased figure size for better readability
    
    # Get a list of unique machine IDs and job IDs from the schedule
    machine_ids = sorted(list(set(op[2] for op in schedule)))
    job_ids = sorted(list(set(op[0] for op in schedule)))
    
    # --- Dynamic Color Mapping ---
    # Using a more vibrant colormap with enough distinct colors for jobs
    num_jobs = len(job_ids)
    
    # Use a colormap that cycles through distinct colors
    # 'tab20' is good for up to 20 distinct colors. If more, we can use a custom approach.
    if num_jobs <= 20:
        colors = plt.cm.get_cmap('tab20', num_jobs)
    else:
        # For more than 20 jobs, generate a wider range of distinct colors
        colors = [plt.cm.hsv(i / num_jobs) for i in range(num_jobs)]
    
    color_map = {job_id: colors(i) if num_jobs <= 20 else colors[i] for i, job_id in enumerate(job_ids)}
    
    # Set Y-axis labels to be "Machine X"
    ax.set_yticks([mid for mid in machine_ids]) # Position ticks at the center of bars
    ax.set_yticklabels([f'Machine {mid}' for mid in machine_ids], fontsize=10)
    
    # Set X-axis limits
    max_time = max(op[4] for op in schedule) if schedule else 0
    ax.set_xlim(0, max_time + max_time * 0.1) # Add 10% padding to the right
    
    # Plot each operation as a horizontal bar
    for op in schedule:
        job_id, op_index, machine_id, start_time, end_time = op
        duration = end_time - start_time
        color = color_map[job_id]
        
        # Draw the bar
        ax.barh(machine_id, duration, left=start_time, height=0.7, # Slightly larger bars
                align='center', color=color, edgecolor='white', linewidth=0.8, alpha=0.9) # White edge for separation
        
        # Add text label (Job ID) in the middle of the bar
        ax.text(start_time + duration/2, machine_id, f'J{job_id}', 
                ha='center', va='center', color='black', fontsize=9, fontweight='bold') # Black text for contrast

    ax.set_xlabel('Time Units', fontsize=12)
    ax.set_ylabel('Machines', fontsize=12)
    ax.set_title(title, fontsize=16, pad=20) # Title with more padding

    # Add minor ticks and grid for better readability
    ax.set_xticks(np.arange(0, max_time + max_time * 0.1, 5), minor=True) # Minor ticks every 5 units
    ax.grid(True, which='major', axis='x', linestyle='--', linewidth=0.7, alpha=0.6)
    ax.grid(True, which='minor', axis='x', linestyle=':', linewidth=0.5, alpha=0.4)
    ax.set_axisbelow(True) # Ensure grid is behind the bars

    # --- Create a Legend ---
    # We'll create custom legend handles because barh doesn't automatically create them for a color map
    legend_elements = [
        plt.Rectangle((0, 0), 1, 1, fc=color_map[j_id], edgecolor='white', label=f'Job {j_id}')
        for j_id in job_ids
    ]
    # Place the legend outside the plot, to the right
    ax.legend(handles=legend_elements, bbox_to_anchor=(1.02, 1), loc='upper left', 
              borderaxespad=0., title="Jobs", fontsize=9)
    
    plt.tight_layout(rect=[0, 0, 0.88, 1]) # Adjust layout to make space for the legend
    plt.show()