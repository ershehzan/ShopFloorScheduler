# app.py
import os
from flask import Flask, render_template, request

from data_loader import load_data_from_excel
from main import schedule_spt # We are testing with SPT for now
from visualization import create_gantt_chart
from models import Machine 
import copy

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return "No file part", 400
    file = request.files['file']
    if file.filename == '':
        return "No selected file", 400
    
    if file:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'data.xlsx')
        file.save(filepath)
        
        try:
            machines, jobs_data = load_data_from_excel(filepath)
        except Exception as e:
            return f"Error loading Excel: {e}", 500

        # --- RUN SCHEDULER (Still SPT for testing) ---
        setup_time = 2
        machines_copy = copy.deepcopy(machines)
        schedule_result = schedule_spt(jobs_data, machines_copy, setup_time)
        
        # --- CALCULATE METRICS ---
        makespan = max(op[4] for op in schedule_result) if schedule_result else 0
        
        # Simple tardiness calc (same logic as in our other files)
        job_completion = {}
        for op in schedule_result:
            job_completion[op[0]] = max(job_completion.get(op[0], 0), op[4])
        job_map = {j.job_id: j for j in jobs_data}
        tardiness = sum(max(0, job_completion[jid] - job_map[jid].due_date) for jid in job_completion)

        # --- GENERATE CHART ---
        chart_filename = 'result_chart.png'
        chart_path = os.path.join('static', chart_filename)
        # Note: We pass save_path to save it, not show it
        create_gantt_chart(schedule_result, "Optimized Schedule", save_path=chart_path)
        
        # --- RENDER RESULTS PAGE ---
        # We pass variables (makespan, tardiness, filename) to the HTML
        return render_template('results.html', 
                               makespan=makespan, 
                               tardiness=tardiness, 
                               chart_filename=chart_filename)

if __name__ == '__main__':
    app.run(debug=True)