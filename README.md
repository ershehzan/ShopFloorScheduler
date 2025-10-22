# Python-Powered Shop Floor Scheduler 🏭

## 📖 Overview

This is a comprehensive, command-line application built in pure Python to solve complex shop floor scheduling problems. This tool takes real-world inputs (jobs, machines, and constraints) from a Google Sheet, calculates optimized schedules using multiple algorithms, and exports the results, including visual Gantt charts and performance reports, to Excel.

The core of this project is a multi-objective **Genetic Algorithm (GA)** that intelligently balances two competing factory goals: minimizing the total production time (**makespan**) and minimizing job lateness (**tardiness**).

## ✨ Key Features

* **Cloud-Based Input**: Reads all data directly from a Google Sheet using the Google Sheets API.
* **Realistic Constraints**: The scheduling engine accurately handles:
    * **Machine Downtime**: Schedules work *around* predefined maintenance windows.
    * **Setup Times**: Automatically adds time when a machine switches between different jobs.
* **Multiple Scheduling Algorithms**:
    * **Simple Rules**: First-Come First-Served (FCFS), Shortest Processing Time (SPT), Earliest Due Date (EDD), and Weighted Shortest Processing Time (WSPT).
    * **Advanced AI**: A complete **Genetic Algorithm (GA)** built from scratch.
* **Multi-Objective Optimization**: The Genetic Algorithm is configurable to find the "best" schedule by balancing a weighted score between **makespan** and **tardiness**.
* **Professional Output**: For each algorithm, the program automatically generates:
    * A **Gantt Chart** visualization (using `matplotlib`).
    * A detailed **Excel Report** with a full schedule and performance metrics (using `pandas`).
* **Robust & Configurable**:
    * All key settings (like `setup_time` and GA weights) are controlled via an external `config.ini` file.
    * Includes robust error handling for missing files, bad data, and API connection issues.

## 🚀 How It Works

[Architecture Diagram - We will add this later]

1.  **Load Data**: The `data_loader.py` securely connects to the Google Sheets API using `credentials.json`, fetches the job and machine data, and parses it into Python objects.
2.  **Read Config**: The `main.py` script reads settings like `setup_time` and GA fitness weights from `config.ini`.
3.  **Run Schedulers**: The application runs all scheduling algorithms (FCFS, SPT, EDD, WSPT) on the dataset.
4.  **Evolve Solution**: The `genetic_algorithm.py` module creates an initial population of random schedules and evolves them over 50 generations, using selection, crossover, and mutation to find a near-optimal solution based on the multi-objective fitness score.
5.  **Generate Output**: The `exporter.py` and `visualization.py` modules take the final schedules and save them as `.xlsx` files and Gantt chart images in the `output/` folder.

## 🛠️ Installation & Setup

Follow these steps to set up and run the project on your local machine.

### 1. Prerequisites
* Python 3.8 or newer
* A Google Cloud account
* A Google Sheet (you can copy [this template](https://docs.google.com/spreadsheets/d/YOUR_SHEET_URL/edit?usp=sharing))

### 2. Clone & Install
```bash
# 1. Clone the repository
git clone [https://github.com/ershehzan/ShopFloorScheduler.git](https://github.com/ershehzan/ShopFloorScheduler.git)
cd ShopFloorScheduler

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows, use: .\.venv\Scripts\activate

# 3. Install the required libraries
pip install pandas openpyxl matplotlib gspread google-auth-oauthlib

🚀 How to Use the Program
1. Configure Your Input
Google Sheet (ShopFloorData):

Machines Sheet: Must have columns machine_id and unavailable_periods (e.g., 10-15;40-45).

Jobs Sheet: Must have columns job_id, operations (e.g., 0(5);2(8)), due_date, and priority.

Config File (config.ini):

[Settings]: Change the setup_time for machines.

[GeneticAlgorithm]: Adjust the behavior of the GA, including population_size, num_generations, and the fitness weights (makespan_weight, tardiness_weight).

2. Run the Scheduler
With your virtual environment active, simply run:
python main.py