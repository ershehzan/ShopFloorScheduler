# app.py
import os
from flask import Flask, render_template, request, send_file

# --- Custom Modules ---
from data_loader import load_data_from_excel
from main import schedule_spt # We are still using SPT for one more day
from visualization import create_gantt_chart
from exporter import export_to_excel
from models import Machine 
import copy

app = Flask(__name__)

# Configure folders
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'
if not os.path.exists(UPLOAD_FOLDER): os.makedirs(UPLOAD_FOLDER)
if not os.path.exists(OUTPUT_FOLDER): os.makedirs(OUTPUT_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    # --- 1. Handle File Upload ---
    if 'file' not in request.files: return "No file part", 400
    file = request.files['file']
    if file.filename == '': return "No selected file", 400
    
    if file:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'data.xlsx')
        file.save(filepath)
        
        try:
            machines, jobs_data = load_data_from_excel(filepath)
        except Exception as e:
            return f"Error loading Excel: {e}", 500

        # --- 2. Read Settings from HTML Form ---
        # We use 'request.form.get(name, default_value)'
        try:
            setup_time = int(request.form.get('setup_time', 2))
            
            # We will use these GA settings tomorrow, getting them ready now:
            pop_size = int(request.form.get('pop_size', 30))
            generations = int(request.form.get('generations', 50))
            w_makespan = float(request.form.get('w_makespan', 0.6))
            w_tardiness = float(request.form.get('w_tardiness', 0.4))
            
        except ValueError:
            return "Error: Invalid number provided in settings.", 400

        # --- 3. Run Scheduler ---
        # NOTE: Today we are still running SPT to test the input.
        # SPT only uses 'setup_time'. Tomorrow we connect the GA!
        
        machines_copy = copy.deepcopy(machines)
        schedule_result = schedule_spt(jobs_data, machines_copy, setup_time)
        
        # --- 4. Metrics & Output ---
        makespan = max(op[4] for op in schedule_result) if schedule_result else 0
        
        job_completion = {}
        for op in schedule_result:
            job_completion[op[0]] = max(job_completion.get(op[0], 0), op[4])
        job_map = {j.job_id: j for j in jobs_data}
        tardiness = sum(max(0, job_completion[jid] - job_map[jid].due_date) for jid in job_completion)

        # Save assets
        chart_filename = 'result_chart.png'
        chart_path = os.path.join('static', chart_filename)
        create_gantt_chart(schedule_result, "Optimized Schedule", save_path=chart_path)
        
        excel_filename = 'optimized_schedule.xlsx'
        excel_path = os.path.join(app.config['OUTPUT_FOLDER'], excel_filename)
        export_to_excel(schedule_result, jobs_data, excel_path)

        # Render Page
        return render_template('results.html', 
                               makespan=makespan, 
                               tardiness=tardiness, 
                               chart_filename=chart_filename,
                               excel_filename=excel_filename)

@app.route('/download/<filename>')
def download_file(filename):
    path = os.path.join(app.config['OUTPUT_FOLDER'], filename)
    return send_file(path, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)