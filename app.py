 # app.py
import os
import threading
import uuid
import copy
from flask import Flask, render_template, request, send_file, jsonify

# --- Custom Modules ---
from data_loader import load_data_from_excel
from genetic_algorithm import run_genetic_algorithm
from visualization import create_gantt_chart
from exporter import export_to_excel

app = Flask(__name__)

# Configure folders
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'
STATIC_FOLDER = 'static'
for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER, STATIC_FOLDER]:
    if not os.path.exists(folder): os.makedirs(folder)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER

# --- GLOBAL STORAGE FOR BACKGROUND TASKS ---
# In a real production app, we would use a database (Redis/SQL).
# For this project, a simple dictionary is perfect.
JOBS = {} 

@app.route('/')
def home():
    return render_template('index.html')

# --- WORKER FUNCTION (Runs in Background) ---
def process_schedule(task_id, filepath, setup_time, pop_size, gens, w_makespan, w_tardiness):
    """This runs inside a separate thread so it doesn't block the UI."""
    try:
        JOBS[task_id]['message'] = "Loading Data..."
        machines, jobs_data = load_data_from_excel(filepath)
        machines_copy = copy.deepcopy(machines)

        JOBS[task_id]['message'] = "Running Genetic Algorithm..."
        
        # Run GA
        schedule_result = run_genetic_algorithm(
            jobs_data, machines_copy, setup_time,
            pop_size, gens, 0.1, 3, w_makespan, w_tardiness
        )

        JOBS[task_id]['message'] = "Generating Reports..."

        # Calculate Metrics
        makespan = max(op[4] for op in schedule_result) if schedule_result else 0
        job_completion = {}
        for op in schedule_result:
            job_completion[op[0]] = max(job_completion.get(op[0], 0), op[4])
        job_map = {j.job_id: j for j in jobs_data}
        tardiness = sum(max(0, job_completion[jid] - job_map[jid].due_date) for jid in job_completion)

        # Save Assets (Unique filenames using task_id to prevent conflicts)
        chart_filename = f'chart_{task_id}.png'
        chart_path = os.path.join(STATIC_FOLDER, chart_filename)
        create_gantt_chart(schedule_result, "Genetic Algorithm Schedule", save_path=chart_path)
        
        excel_filename = f'schedule_{task_id}.xlsx'
        excel_path = os.path.join(app.config['OUTPUT_FOLDER'], excel_filename)
        export_to_excel(schedule_result, jobs_data, excel_path)

        # Save Results to Global Dictionary
        JOBS[task_id]['result'] = {
            'makespan': makespan,
            'tardiness': tardiness,
            'chart': chart_filename,
            'excel': excel_filename
        }
        JOBS[task_id]['state'] = 'complete'

    except Exception as e:
        JOBS[task_id]['state'] = 'error'
        JOBS[task_id]['message'] = str(e)

# --- ROUTES ---

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files: return "No file part", 400
    file = request.files['file']
    if file.filename == '': return "No selected file", 400
    
    if file:
        # Generate a unique ID for this specific run
        task_id = str(uuid.uuid4())
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{task_id}.xlsx")
        file.save(filepath)

        # Read form data
        try:
            setup_time = int(request.form.get('setup_time', 2))
            pop_size = int(request.form.get('pop_size', 30))
            generations = int(request.form.get('generations', 50))
            w_makespan = float(request.form.get('w_makespan', 0.6))
            w_tardiness = float(request.form.get('w_tardiness', 0.4))
        except ValueError:
            return "Invalid settings", 400

        # Initialize Task in Global Dictionary
        JOBS[task_id] = {'state': 'processing', 'message': 'Initializing...'}

        # Start Background Thread
        thread = threading.Thread(target=process_schedule, args=(
            task_id, filepath, setup_time, pop_size, generations, w_makespan, w_tardiness
        ))
        thread.start()

        # Immediately send user to loading page (passing the task_id)
        return render_template('loading.html', task_id=task_id)

@app.route('/status/<task_id>')
def check_status(task_id):
    """Called by JavaScript to check progress."""
    return jsonify(JOBS.get(task_id, {'state': 'error', 'message': 'Unknown Task'}))

@app.route('/results/<task_id>')
def show_results(task_id):
    """Render the final results page."""
    job = JOBS.get(task_id)
    if not job or job['state'] != 'complete':
        return "Job not found or not ready", 404
    
    res = job['result']
    return render_template('results.html', 
                           makespan=res['makespan'], 
                           tardiness=res['tardiness'], 
                           chart_filename=res['chart'],
                           excel_filename=res['excel'])

@app.route('/download/<filename>')
def download_file(filename):
    path = os.path.join(app.config['OUTPUT_FOLDER'], filename)
    return send_file(path, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
