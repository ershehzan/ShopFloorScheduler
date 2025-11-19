# Python-Powered Shop Floor Scheduler 🏭

## 📖 Overview

This is a comprehensive, command-line application built in pure Python to solve complex shop floor scheduling problems. This tool takes real-world inputs (jobs, machines, and constraints) from a local **Excel file (`data.xlsx`)**, calculates optimized schedules using multiple algorithms, and exports the results, including visual Gantt charts and performance reports, back to Excel.

The core of this project is a multi-objective **Genetic Algorithm (GA)** that intelligently balances two competing factory goals: minimizing the total production time (**makespan**) and minimizing job lateness (**tardiess**).

## ✨ Key Features

* **Local Excel Input**: Reads all data directly from `data.xlsx` using `pandas`.
* **Realistic Constraints**: The scheduling engine accurately handles:
    * **Machine Downtime**: Schedules work *around* predefined maintenance windows specified in Excel.
    * **Setup Times**: Automatically adds time when a machine switches between different jobs, configured via `config.ini`.
* **Multiple Scheduling Algorithms**:
    * **Simple Rules**: First-Come First-Served (FCFS), Shortest Processing Time (SPT), Earliest Due Date (EDD), and Weighted Shortest Processing Time (WSPT).
    * **Advanced AI**: A complete **Genetic Algorithm (GA)** built from scratch.
* **Multi-Objective Optimization**: The Genetic Algorithm is configurable via `config.ini` to find the "best" schedule by balancing a weighted score between **makespan** and **tardiess**.
* **Professional Output**: For each algorithm, the program automatically generates:
    * A **Gantt Chart** visualization (using `matplotlib`).
    * A detailed **Excel Report** with a full schedule and performance metrics (using `pandas`), saved in the `output/` folder.
* **Robust & Configurable**:
    * All key settings (like `setup_time` and GA weights) are controlled via the external `config.ini` file.
    * Includes robust error handling for missing files, bad data formats, and incorrect configurations.

## 🚀 How It Works

[Architecture Diagram - Placeholder]

1.  **Load Data**: The `data_loader.py` module reads the `Machines` and `Jobs` sheets from `data.xlsx` using `pandas` and parses the data into Python objects (`Machine`, `Job`, `Operation`).
2.  **Read Config**: The `main.py` script reads settings like `setup_time` and GA fitness weights from `config.ini`, using default values if the file or settings are missing.
3.  **Run Schedulers**: The application runs all scheduling algorithms (FCFS, SPT, EDD, WSPT) on the dataset.
4.  **Evolve Solution**: The `genetic_algorithm.py` module creates an initial population of random schedules and evolves them over multiple generations (configured in `config.ini`), using selection, crossover, and mutation to find a near-optimal solution based on the multi-objective fitness score.
5.  **Generate Output**: The `exporter.py` and `visualization.py` modules take the final schedules and save them as `.xlsx` files and display Gantt chart images.
<<<<<<< HEAD
=======

  ## Author
   ### Shehzan Khan
💻 *Aspiring Software Developer | Problem Solver*
📫 [GitHub](https://github.com/ershehzan) | [LinkedIn](https://www.linkedin.com/in/shehzankhan/)
>>>>>>> ec5e38ac9af819bc60e7b670a6a103dd3ee8fd51

## 🛠️ Installation & Setup

Follow these steps to set up and run the project on your local machine.

### 1. Prerequisites
* Python 3.8 or newer
* Microsoft Excel or a compatible spreadsheet program

### 2. Clone & Install
```bash
# 1. Clone the repository
git clone [https://github.com/ershehzan/ShopFloorScheduler.git](https://github.com/ershehzan/ShopFloorScheduler.git)
cd ShopFloorScheduler

# 2. Create and activate a virtual environment
python -m venv .venv
# On Windows:
.\.venv\Scripts\activate
# On macOS/Linux:
# source .venv/bin/activate

# 3. Install the required libraries
<<<<<<< HEAD
pip install pandas openpyxl matplotlib
=======
pip install pandas openpyxl matplotlib


>>>>>>> ec5e38ac9af819bc60e7b670a6a103dd3ee8fd51
