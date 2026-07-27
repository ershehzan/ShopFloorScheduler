# PyShop Scheduler : Shop Floor Scheduling Optimization

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-teal)
![Next.js](https://img.shields.io/badge/Next.js-15-black)
![TypeScript](https://img.shields.io/badge/TypeScript-5-blue)
![License](https://img.shields.io/badge/License-MIT-orange)
![Tests](https://img.shields.io/badge/Tests-195%20passed-brightgreen)

**PyShop Scheduler** is a full-stack, AI-powered production scheduling and optimization system designed to solve complex Job Shop Scheduling problems. It features a **FastAPI** backend driven by a **Multi-Objective Genetic Algorithm (GA)**, a **Reinforcement Learning optimizer**, and a modern **Next.js** dashboard with real-time WebSocket updates.

This tool helps factory managers optimize production by intelligently balancing **Makespan** (total time) and **Tardiness** (missed deadlines), achieving results that are often **20–30% faster** than standard heuristic rules.

---

## Key Features

### Intelligent Scheduling Engine
* **Genetic Algorithm (GA):** A custom-built metaheuristic that evolves schedules over generations using tournament selection, ordered crossover (OX1), and swap mutation.
* **Multi-Objective Optimization:** Minimizes a weighted combination of makespan and total tardiness simultaneously.
* **Heuristic Algorithms:** FCFS, SPT (Shortest Processing Time), EDD (Earliest Due Date), and WSPT (Weighted SPT).
* **Reinforcement Learning (RL):** Tabular Q-learning agent that learns optimal job sequencing through thousands of environment interactions.
* **Real Constraints:** Machine downtime (maintenance windows), setup times between different jobs, and shift-window scheduling.

### Modern Web Interface
* **Interactive Dashboard:** Built with **Next.js 15** (App Router) and TypeScript — responsive, dark-mode, glassmorphic design.
* **Visual Gantt Charts:** Auto-generated Matplotlib Gantt charts displayed in the browser.
* **Real-Time Progress:** WebSocket integration shows live optimization progress during GA and RL runs.
* **Algorithm Comparison:** Side-by-side benchmarking of all algorithms on the same dataset.
* **Detailed Reports:** Download full Excel (`xlsx`) or PDF schedule reports per run.
* **Run History:** Paginated, filterable table of all historical scheduling runs with full metrics.

### Dynamic Configuration
* **User Controls:** Adjust GA population size, generations, mutation rate, makespan/tardiness weights, and setup time from the UI.
* **Asynchronous Processing:** Background threading keeps the API responsive; all task state is persisted to SQLite so it survives server restarts.
* **Dynamic Rescheduling:** Inject machine breakdowns or rush orders into completed schedules to generate an updated plan.

### Enterprise & AI Features
* **JWT Authentication:** Register, login, refresh, and logout with short-lived access tokens and long-lived refresh tokens.
* **Predictive Maintenance:** Isolation Forest anomaly detection on synthetic sensor telemetry (temperature, vibration, load). Generates severity-ranked maintenance alerts with recommended actions.
* **Digital Twin Simulation:** Discrete-event simulator replays a completed schedule in virtual time over WebSocket, supporting mid-simulation disruption injection (breakdowns, rush orders).
* **Machine Shift Management:** CRUD interface to define per-machine working shift windows (start, end, cycle length). Shift-aware FCFS scheduler respects these windows automatically.
* **AI Scheduling Assistant:** Rule-based natural language agent answers questions about your latest run, machine utilization, late jobs, maintenance alerts, and algorithm comparisons — directly in a chat UI.
* **Manual Gantt Editor:** PATCH a completed run's schedule with manually adjusted operation times; the system detects conflicts and recomputes all KPIs.

### Analytics & Reporting
* **Analytics Dashboard:** Trend charts (makespan over time), utilization heatmaps per machine per run, tardiness distribution histograms, and algorithm comparison tables.
* **KPI Cards:** Makespan, total tardiness, average flow time, on-time delivery %, and machine utilization for every run.
* **PDF & Excel Export:** Multi-sheet Excel workbooks and styled PDF reports downloadable per run.

---

## Prerequisites

Before running **PyShop Scheduler**, ensure you have the following installed on your machine:

* **Python:** `3.10` or higher
* **Node.js:** `v18.0` or higher (with `npm` v9+)
* **Git:** Version control
* *(Optional)* **Docker & Docker Compose:** For running the full stack containerized with PostgreSQL and Redis

---

## Quick Start Guide

### Step 1: Clone the Repository

```bash
git clone https://github.com/ershehzan/ShopFloorScheduler.git
cd ShopFloorScheduler
```

### Step 2: Set Up Python Environment

1. Create a Python virtual environment:
   ```bash
   # Windows
   python -m venv .venv
   .\.venv\Scripts\activate

   # Linux / macOS
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install Python dependencies:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

### Step 3: Environment Configuration

Copy the example environment file to create your `.env` file:

```bash
# Windows (PowerShell)
copy .env.example .env

# Linux / macOS / Git Bash
cp .env.example .env
```

Default key configuration in `.env`:
```ini
DATABASE_URL=sqlite:///./shopfloor.db
JWT_SECRET_KEY=your-secret-key-here
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Step 4: Install Frontend Dependencies

```bash
cd frontend
npm install
cd ..
```

---

## How to Run the Project

You can run **PyShop Scheduler** using any of the following methods depending on your workflow:

### Method 1: Full-Stack Web Application (Recommended)

Run the backend FastAPI server and Next.js frontend concurrently in separate terminal windows:

#### 1. Start the FastAPI Backend (Terminal 1)
```bash
# Activate virtual environment if not already activated
# Windows: .\.venv\Scripts\activate | Linux/Mac: source .venv/bin/activate

uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```
* **API Server:** `http://localhost:8000`
* **Swagger API Documentation:** `http://localhost:8000/docs`
* **ReDoc Documentation:** `http://localhost:8000/redoc`

#### 2. Start the Next.js Frontend (Terminal 2)
```bash
cd frontend
npm run dev
```
* **Web Dashboard:** `http://localhost:3000`

---

### Method 2: Docker Compose (All-in-One Stack)

To run the complete system (FastAPI backend, Next.js frontend, PostgreSQL database, and Redis cache) inside Docker containers:

```bash
# Build and start all services in detached mode
docker-compose up --build -d

# View real-time container logs
docker-compose logs -f

# Stop and remove containers
docker-compose down
```

Access services:
* **Frontend Web App:** `http://localhost:3000`
* **FastAPI Backend:** `http://localhost:8000`
* **Interactive API Docs:** `http://localhost:8000/docs`

---

### Method 3: Command-Line Interface (CLI / Headless Script)

If you want to run scheduling algorithms directly against an Excel spreadsheet without launching web servers:

1. Ensure input file `data.xlsx` is present in the project root directory.
2. Run the main batch processing script:

```bash
python main.py
```

This will:
* Load configuration from `config.ini`
* Run FCFS, SPT, EDD, WSPT heuristics and the Genetic Algorithm
* Display a formatted performance comparison table in your console
* Save generated Gantt charts (`PNG`) and detailed schedule workbooks (`XLSX`) into the `output/` directory.

---

### Method 4: Legacy Standalone Flask App (Optional)

For simplified lightweight testing using the legacy single-file Flask web UI:

```bash
python app.py
```

Access legacy interface:
* **Flask Web Interface:** `http://localhost:5000`

---

## Input Data Format

When uploading schedule datasets or running `main.py`, your input Excel file (`.xlsx`) must contain two sheets:

1. **`Machines` Sheet:**
   | Column Name | Description | Example |
   |---|---|---|
   | `machine_id` | Unique ID for machine | `M1`, `M2`, `M3` |
   | `unavailable_periods` | List of maintenance downtime windows `(start, end)` | `[(10, 20), (50, 60)]` |

2. **`Jobs` Sheet:**
   | Column Name | Description | Example |
   |---|---|---|
   | `job_id` | Unique ID for job | `J1`, `J2` |
   | `operations` | Operations list `[(machine_id, duration), ...]` | `[("M1", 5), ("M2", 3)]` |
   | `due_date` | Target completion deadline | `25` |
   | `priority` | Priority multiplier | `1` or `2` |

A sample `data.xlsx` file is included in the project root for reference.

---

## Running Database Migrations

Database tables are initialized automatically on FastAPI startup. If you make schema changes, apply Alembic migrations using:

```bash
# Apply pending migrations
alembic upgrade head

# Generate a new migration revision
alembic revision --autogenerate -m "describe changes"
```

---

## Running Automated Tests

Run the comprehensive test suite with `pytest`:

```bash
# Run all tests
python -m pytest tests/ -v

# Run tests with output logging
python -m pytest tests/ -v -s

# Run a specific test module (e.g., shifts or auth)
python -m pytest tests/test_shifts.py -v
python -m pytest tests/test_auth.py -v
```

---

## API Overview

| Group | Route | Method | Description |
|---|---|---|---|
| Health | `/health` | GET | System health check |
| Auth | `/api/auth/register` | POST | Create a new user account |
| Auth | `/api/auth/login` | POST | Login and receive JWT tokens |
| Auth | `/api/auth/refresh` | POST | Refresh access token |
| Auth | `/api/auth/me` | GET | Current user profile |
| Schedule | `/api/schedule/upload` | POST | Upload Excel and start optimization |
| Schedule | `/api/schedule/status/{id}` | GET | Poll task status |
| Schedule | `/api/schedule/results/{id}` | GET | Fetch completed results |
| Schedule | `/api/schedule/compare` | POST | Run all algorithms side-by-side |
| Schedule | `/api/schedule/{id}/manual` | PATCH | Commit a manually edited Gantt |
| Schedule | `/api/schedule/download/{fn}` | GET | Download Excel report |
| History | `/api/history` | GET | Paginated run history |
| Analytics | `/api/analytics/summary` | GET | Aggregate KPIs |
| Analytics | `/api/analytics/trends` | GET | Time-series trend data |
| Analytics | `/api/analytics/utilization-heatmap` | GET | Machine utilization heatmap |
| Reschedule | `/api/reschedule/breakdown` | POST | Machine breakdown rescheduling |
| Reschedule | `/api/reschedule/rush-order` | POST | Rush order injection |
| WebSocket | `/ws/progress/{task_id}` | WS | Real-time task progress |
| Maintenance | `/api/maintenance/ingest` | POST | Ingest sensor readings |
| Maintenance | `/api/maintenance/alerts` | GET | Active maintenance alerts |
| Maintenance | `/api/maintenance/forecast` | GET | Failure probability forecast |
| RL | `/api/rl/train` | POST | Start RL training run |
| RL | `/api/rl/status/{id}` | GET | Training status |
| Digital Twin | `/api/twin/start` | POST | Start a twin simulation session |
| Digital Twin | `/api/twin/{id}/inject` | POST | Inject a disruption |
| Shifts | `/api/shifts` | GET / POST | List / create shift windows |
| Shifts | `/api/shifts/{id}` | PUT / DELETE | Update / delete a shift |
| Assistant | `/api/assistant/chat` | POST | Chat with the scheduling assistant |
| Assistant | `/api/assistant/prompts` | GET | Suggested starter prompts |

---

## Tech Stack

* **Backend:** Python 3.10+, FastAPI, Pydantic v2, SQLAlchemy 2.x, Loguru, Uvicorn
* **Database:** SQLite (default) / PostgreSQL (via `DATABASE_URL`)
* **Algorithms:** Genetic Algorithm, Q-Learning (RL), Isolation Forest (ML), FCFS / SPT / EDD / WSPT
* **Frontend:** TypeScript, React, Next.js 15 (App Router), Tailwind CSS, Recharts
* **Real-Time:** WebSockets (FastAPI `websockets`), background threading
* **Auth:** JWT (python-jose, passlib/bcrypt)
* **Reporting:** Pandas, openpyxl (Excel), ReportLab (PDF), Matplotlib (Gantt PNG)
* **DevOps:** Docker, docker-compose, `.env` configuration

---

## Development Roadmap

| Phase | Status | Highlights |
|---|---|---|
| Phase 1 — Core Infrastructure | ✅ Complete | FastAPI, SQLite, scheduling algorithms, Gantt, history API |
| Phase 2 — Production Readiness | ✅ Complete | Bug fixes, 59-test suite, full DB persistence |
| Phase 3 — Enterprise Features | ✅ Complete | JWT auth, WebSockets, analytics dashboard, rescheduling, Docker |
| Phase 4 — Advanced Intelligence | ✅ Complete | Predictive maintenance, RL optimizer, Digital Twin, 3 AI dashboards |
| Phase 5 — Collaboration & Intelligence | ✅ Complete | Shift management, AI assistant chat, manual Gantt editor |

---

© 2025 Shehzan Khan. Created as a personal portfolio project.
