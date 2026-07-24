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

## Quick Start Guide

### 1. Clone & Install

```bash
git clone https://github.com/ershehzan/ShopFloorScheduler.git
cd ShopFloorScheduler

# Create virtual environment
python -m venv .venv
# Activate (Windows)
.\.venv\Scripts\activate
# Activate (Mac/Linux)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

Key variables:

```
DATABASE_URL=sqlite:///./shopfloor.db   # or postgresql://user:pass@host/db
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
ALLOWED_ORIGINS=http://localhost:3000
```

### 3. Prepare Data

Your input file must be an Excel file (`.xlsx`) with two sheets:

* **`Machines`**: Columns: `machine_id`, `unavailable_periods`
* **`Jobs`**: Columns: `job_id`, `operations`, `due_date`, `priority`

A sample `data.xlsx` is included in the repository.

### 4. Run the Backend

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

Swagger UI → **`http://localhost:8000/docs`**

### 5. Run the Frontend

```bash
cd frontend
npm install
npm run dev
```

Open your browser → **`http://localhost:3000`**

### 6. (Optional) Docker — Run Everything

```bash
docker-compose up --build
```

This starts the FastAPI backend, Next.js frontend, and (optionally) Redis for Celery workers.

---

## Running Tests

```bash
# Run all 195 tests
.venv\Scripts\python -m pytest tests/ -v

# Run a specific module
.venv\Scripts\python -m pytest tests/test_shifts.py -v
```

Test modules cover: engine, metrics, GA, data loader, API endpoints, auth, analytics, WebSockets, rescheduler, maintenance, RL, digital twin, shifts, and manual Gantt editor.

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
