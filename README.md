# PyShop Scheduler: Shop Floor Scheduling Optimization 🏭

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Flask](https://img.shields.io/badge/Flask-Web%20App-green)
![Bootstrap](https://img.shields.io/badge/UI-Bootstrap%205-purple)
![License](https://img.shields.io/badge/License-MIT-orange)

**PyShop Scheduler** is a full-stack optimization tool designed to solve complex Job Shop Scheduling problems. It features a powerful Python backend driven by a **Multi-Objective Genetic Algorithm (GA)** and a modern, user-friendly Web Interface.

This tool helps factory managers optimize production by intelligently balancing **Makespan** (total time) and **Tardiness** (missed deadlines), achieving results that are often **20-30% faster** than standard heuristic rules.

---

## ✨ Key Features

### 🧠 Intelligent Scheduling Engine
* **Genetic Algorithm:** A custom-built metaheuristic that evolves schedules over generations.
* **Multi-Objective:** Optimizes for both speed and on-time delivery simultaneously.
* **Real Constraints:** Handles complex constraints like **Machine Downtime** (maintenance) and **Setup Times**.

### 💻 Modern Web Interface
* **Interactive Dashboard:** Built with **Flask** and **Bootstrap 5**.
* **Drag-and-Drop Upload:** Easily upload Excel schedule data.
* **Visual Gantt Charts:** Automatically generates and displays detailed production timelines.
* **Detailed Reports:** View row-by-row schedule data or download full Excel reports.

### ⚙️ Dynamic Configuration
* **User Controls:** Adjust population size, generations, and fitness weights directly from the UI.
* **Asynchronous Processing:** Features a real-time loading screen for handling long-running tasks.

---

## 🚀 Quick Start Guide

### 1. Clone & Install
```bash
git clone [https://github.com/ershehzan/ShopFloorScheduler.git](https://github.com/ershehzan/ShopFloorScheduler.git)
cd ShopFloorScheduler

# Create virtual environment
python -m venv .venv
# Activate (Windows)
.\.venv\Scripts\activate
# Activate (Mac/Linux)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
````

*(Note: If you don't have a `requirements.txt`, install manually: `pip install flask pandas openpyxl matplotlib`)*

### 2\. Prepare Data

Your input file must be an Excel file (`.xlsx`) with two sheets:

  * **`Machines`**: Columns: `machine_id`, `unavailable_periods`
  * **`Jobs`**: Columns: `job_id`, `operations`, `due_date`, `priority`

### 3\. Run the Application

```bash
python app.py
```

Open your browser and navigate to: **`http://127.0.0.1:5000`**

-----

## 🛠️ Tech Stack

  * **Backend:** Python, Pandas (Data Processing), Matplotlib (Visualization)
  * **Frontend:** HTML5, CSS3, Bootstrap 5, JavaScript (Polling)
  * **Web Framework:** Flask
  * **Algorithms:** Genetic Algorithm, Heuristics (SPT, EDD, WSPT)

-----

© 2025 Shehzan Khan. Created as a personal portfolio project.

