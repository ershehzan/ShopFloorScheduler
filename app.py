# app.py
import os
from flask import Flask, render_template, request

# --- Import our custom modules ---
from data_loader import load_data_from_excel
from main import schedule_spt # We will start by testing SPT
from visualization import create_gantt_chart
from models import Machine # Needed for deepcopy logic inside schedulers usually, but data_loader handles creation

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
        # 1. Save the uploaded file
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'data.xlsx')
        file.save(filepath)
        
        # 2. Load the data using our logic
        try:
            machines, jobs_data = load_data_from_excel(filepath)
        except Exception as e:
            return f"Error loading Excel: {e}", 500

        # 3. Run a Scheduler (Testing with SPT for now)
        # We use a default setup time of 2 for now
        setup_time = 2
        
        # Create a deepcopy of machines (important!)
        machines_copy = copy.deepcopy(machines)
        
        schedule_result = schedule_spt(jobs_data, machines_copy, setup_time)
        
        # 4. Generate and SAVE the Chart
        # We save it to the 'static' folder so the web browser can see it
        chart_path = os.path.join('static', 'spt_chart.png')
        create_gantt_chart(schedule_result, "SPT Schedule", save_path=chart_path)
        
        return "Success! The scheduler ran and the chart was saved to 'static/spt_chart.png'."

if __name__ == '__main__':
    app.run(debug=True)