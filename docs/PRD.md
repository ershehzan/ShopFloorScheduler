# Product Requirements Document (PRD)

# ShopFloorScheduler

### AI-Powered Production Scheduling and Optimization System

**Version:** 1.0
**Author:** Shehzan Khan
**Date:** June 2026
**Status:** Draft

---

# 1. Product Overview

## Product Vision

ShopFloorScheduler is an AI-powered production scheduling system designed to optimize manufacturing workflows by automatically generating efficient production schedules while minimizing makespan, tardiness, and machine idle time.

The platform assists production planners in creating optimized schedules using heuristic and evolutionary algorithms, enabling smarter decision-making and improved shop floor efficiency.

---

# 2. Problem Statement

Manufacturing organizations often rely on spreadsheets and manual scheduling methods to allocate jobs to machines.

This approach leads to:

* Increased production delays.
* Low machine utilization.
* High operational costs.
* Inefficient resource allocation.
* Difficulty handling dynamic production changes.
* Human errors during scheduling.

Existing ERP systems often lack advanced optimization capabilities.

A smart scheduling engine is required to automatically generate near-optimal schedules while considering real-world constraints.

---

# 3. Goals

## Business Goals

### BG-1

Reduce production makespan by at least **20%**.

### BG-2

Improve machine utilization by **15%**.

### BG-3

Reduce late job deliveries by **25%**.

### BG-4

Decrease manual scheduling effort by **70%**.

---

## Product Goals

* Automate shop floor scheduling.
* Generate optimized schedules in real time.
* Support multiple scheduling algorithms.
* Visualize schedules clearly.
* Enable planners to compare scheduling strategies.
* Adapt schedules during production disruptions.

---

# 4. Target Users

## Primary Users

### Production Planner

Responsible for creating and optimizing production schedules.

### Operations Manager

Monitors overall production efficiency.

### Factory Manager

Tracks resource utilization and production KPIs.

---

## Secondary Users

* Plant Supervisors
* Industrial Engineers
* Manufacturing Analysts

---

# 5. User Personas

## Persona 1: Production Planner

### Pain Points

* Manual scheduling consumes significant time.
* Difficult to balance machine workloads.
* Frequent rescheduling due to unexpected disruptions.

### Needs

* One-click schedule generation.
* Easy schedule comparison.
* Interactive visual timeline.

---

## Persona 2: Factory Manager

### Pain Points

* Lack of visibility into machine utilization.
* Difficulty identifying bottlenecks.

### Needs

* Analytics dashboard.
* Utilization reports.
* Performance metrics.

---

# 6. Core Features

## Feature 1: Production Data Upload

Users can upload:

* Job details
* Machine information
* Processing times
* Due dates

Supported formats:

* CSV
* Excel

### Priority: P0

---

## Feature 2: Schedule Generation Engine

Generate schedules using:

### Heuristic Algorithms

* First Come First Serve (FCFS)
* Shortest Processing Time (SPT)
* Earliest Due Date (EDD)

### Metaheuristic Algorithms

* Genetic Algorithm (GA)

### Future Enhancements

* Simulated Annealing
* Tabu Search
* Particle Swarm Optimization

### Priority: P0

---

## Feature 3: Optimization Metrics

System computes:

* Makespan
* Total Tardiness
* Average Flow Time
* Machine Utilization
* Throughput

### Priority: P0

---

## Feature 4: Interactive Gantt Chart Visualization

Features:

* Machine-wise schedule view
* Zoom functionality
* Task highlighting
* Real-time updates
* Tooltips for job details

### Priority: P0

---

## Feature 5: Comparative Algorithm Analysis

Users can compare multiple scheduling approaches.

Example:

| Algorithm | Makespan | Tardiness |
| --------- | -------- | --------- |
| FCFS      | 450      | 120       |
| SPT       | 390      | 70        |
| GA        | 310      | 25        |

### Priority: P1

---

## Feature 6: Dynamic Rescheduling

System automatically regenerates schedules when:

* Machine breakdown occurs.
* Rush order arrives.
* Processing times change.

### Priority: P1

---

## Feature 7: Constraint Management

Support constraints such as:

* Machine availability
* Due dates
* Job priorities
* Maintenance windows
* Shift schedules

### Priority: P1

---

## Feature 8: Report Generation

Generate downloadable reports.

Formats:

* PDF
* Excel
* CSV

Contents:

* Schedule summary
* Optimization metrics
* Machine statistics

### Priority: P2

---

# 7. User Stories

### US-1

**As a Production Planner,**
I want to upload production jobs so that schedules can be generated automatically.

---

### US-2

**As a Production Planner,**
I want to compare scheduling algorithms so that I can select the most efficient schedule.

---

### US-3

**As a Factory Manager,**
I want to visualize schedules on a Gantt chart so that I can monitor production activities.

---

### US-4

**As an Operations Manager,**
I want the system to dynamically reschedule production after disruptions so that delays are minimized.

---

### US-5

**As a Manufacturing Analyst,**
I want detailed reports so that I can analyze shop floor performance.

---

# 8. Functional Requirements

| ID    | Requirement                         | Priority |
| ----- | ----------------------------------- | -------- |
| FR-1  | Upload job and machine datasets     | High     |
| FR-2  | Generate schedules using heuristics | High     |
| FR-3  | Generate schedules using GA         | High     |
| FR-4  | Display Gantt chart visualization   | High     |
| FR-5  | Compute optimization metrics        | High     |
| FR-6  | Compare multiple algorithms         | Medium   |
| FR-7  | Support dynamic rescheduling        | Medium   |
| FR-8  | Export reports                      | Medium   |
| FR-9  | Manage scheduling constraints       | High     |
| FR-10 | Provide analytics dashboard         | Medium   |

---

# 9. Non-Functional Requirements

| Requirement              | Target                     |
| ------------------------ | -------------------------- |
| Schedule generation time | < 30 seconds               |
| API response time        | < 500 ms                   |
| Concurrent users         | 100+                       |
| Availability             | 99.5%                      |
| Scalability              | Horizontal scaling support |
| Security                 | JWT Authentication         |
| Reliability              | Fault tolerant             |
| Usability                | Simple web interface       |

---

# 10. Success Metrics

| Metric                          | Target  |
| ------------------------------- | ------- |
| Makespan reduction              | ≥20%    |
| Machine utilization improvement | ≥15%    |
| Reduction in tardiness          | ≥25%    |
| Schedule generation time        | <30 sec |
| User satisfaction               | >4/5    |
| System uptime                   | >99%    |

---

# 11. Proposed Industry-Level Architecture

## Frontend

* React.js / Next.js
* TypeScript
* Tailwind CSS
* Recharts

## Backend

* FastAPI
* Celery
* Redis

## Optimization Layer

* Python
* PyGAD
* OR-Tools

## Database

* PostgreSQL

## Infrastructure

* Docker
* Kubernetes

## Deployment

* AWS / GCP

---

# 12. Future Roadmap

### Phase 1 (Current)

✅ Schedule generation
✅ Heuristic algorithms
✅ Genetic Algorithm
✅ Gantt visualization

### Phase 2

* Dynamic rescheduling
* Constraint-based optimization
* Authentication system
* Analytics dashboard

### Phase 3

* Multi-user collaboration
* Real-time shop floor monitoring
* ERP integration

### Phase 4

* Predictive maintenance integration
* Reinforcement Learning optimization
* Digital Twin simulation

---

# 13. Elevator Pitch

**ShopFloorScheduler is an AI-powered production scheduling platform that automatically generates optimized manufacturing schedules using heuristic and evolutionary algorithms, helping factories reduce delays, improve machine utilization, and maximize operational efficiency.**
