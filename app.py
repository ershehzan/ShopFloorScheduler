# app.py
import os
from flask import Flask, render_template, request, redirect, url_for

# Initialize the Flask application
app = Flask(__name__)

# Define the folder where uploaded files will be stored
UPLOAD_FOLDER = 'uploads'
# Ensure the folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/')
def home():
    """Renders the homepage with the upload form."""
    return render_template('index.html')

# --- NEW ROUTE FOR TODAY ---
@app.route('/upload', methods=['POST'])
def upload_file():
    """
    This function runs when the user submits the form.
    It receives the file and saves it to the 'uploads' folder.
    """
    # 1. Check if the post request has the file part
    if 'file' not in request.files:
        return "No file part", 400
    
    file = request.files['file']
    
    # 2. Check if the user selected a file
    if file.filename == '':
        return "No selected file", 400
    
    # 3. Save the file
    if file:
        # We force the name to be 'data.xlsx' so our scheduler always finds it
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'data.xlsx')
        file.save(filepath)
        
        return "File uploaded successfully! (Next step: Run Scheduler)"

if __name__ == '__main__':
    app.run(debug=True)