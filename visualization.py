# visualization.py
import matplotlib
# Use the 'Agg' backend which is non-interactive (perfect for web servers)
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np

def create_gantt_chart(schedule, title="Shop Floor Schedule", save_path=None):
    """
    Generates a Gantt chart. 
    If 'save_path' is provided, saves the image to a file.
    Otherwise, shows it (for local testing).
    """
    if not schedule:
        return

    fig, ax = plt.subplots(figsize=(15, 8))
    
    machine_ids = sorted(list(set(op[2] for op in schedule)))
    job_ids = sorted(list(set(op[0] for op in schedule)))
    
    num_jobs = len(job_ids)
    if num_jobs <= 20:
        colors = plt.cm.get_cmap('tab20', num_jobs)
    else:
        colors = [plt.cm.hsv(i / num_jobs) for i in range(num_jobs)]
    
    color_map = {job_id: colors(i) if num_jobs <= 20 else colors[i] for i, job_id in enumerate(job_ids)}
    
    ax.set_yticks([mid for mid in machine_ids])
    ax.set_yticklabels([f'Machine {mid}' for mid in machine_ids], fontsize=10)
    
    max_time = max(op[4] for op in schedule) if schedule else 0
    ax.set_xlim(0, max_time + max_time * 0.1)
    
    for op in schedule:
        job_id, op_index, machine_id, start_time, end_time = op
        duration = end_time - start_time
        color = color_map[job_id]
        
        ax.barh(machine_id, duration, left=start_time, height=0.7, 
                align='center', color=color, edgecolor='white', linewidth=0.8, alpha=0.9)
        
        ax.text(start_time + duration/2, machine_id, f'J{job_id}', 
                ha='center', va='center', color='black', fontsize=9, fontweight='bold')

    ax.set_xlabel('Time Units', fontsize=12)
    ax.set_ylabel('Machines', fontsize=12)
    ax.set_title(title, fontsize=16, pad=20)

    ax.set_xticks(np.arange(0, max_time + max_time * 0.1, 5), minor=True)
    ax.grid(True, which='major', axis='x', linestyle='--', linewidth=0.7, alpha=0.6)
    ax.grid(True, which='minor', axis='x', linestyle=':', linewidth=0.5, alpha=0.4)
    ax.set_axisbelow(True)

    legend_elements = [
        plt.Rectangle((0, 0), 1, 1, fc=color_map[j_id], edgecolor='white', label=f'Job {j_id}')
        for j_id in job_ids
    ]
    ax.legend(handles=legend_elements, bbox_to_anchor=(1.02, 1), loc='upper left', 
              borderaxespad=0., title="Jobs", fontsize=9)
    
    plt.tight_layout(rect=[0, 0, 0.88, 1])
    
    # --- CHANGE FOR TODAY ---
    if save_path:
        plt.savefig(save_path) # Save to file
        plt.close() # Close memory
        print(f"Chart saved to {save_path}")
    else:
        plt.show()