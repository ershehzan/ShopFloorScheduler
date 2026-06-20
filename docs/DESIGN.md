# 🎨 Design Document

# ShopFloorScheduler

## Enterprise Manufacturing Scheduling Platform

---

# 1. Design Vision

Create an enterprise-grade SaaS experience that communicates:

* **Operational excellence**
* **AI-powered intelligence**
* **Manufacturing precision**
* **Trust & reliability**
* **Real-time decision making**

The UI should feel like:

> "Tesla Dashboard × Linear × Enterprise Manufacturing Software"

Design must emphasize data, automation, and productivity rather than marketing-heavy visuals. ([SkyPlanner][1])

---

# 2. Design Principles

### 1. Clarity First

Complex scheduling data should always remain easy to understand.

### 2. Data-Centric UI

Charts, timelines, KPIs, and tables become primary interface elements.

### 3. Enterprise Simplicity

Avoid unnecessary decorations.

Use whitespace generously.

### 4. Action-Oriented UX

Every screen should guide users toward:

* Create Schedule
* Optimize
* Simulate
* Export

### 5. AI as Assistant

AI recommendations should appear proactive but non-intrusive.

---

# 3. Color System

Inspired by SkyPlanner's industrial blue and Kytes' enterprise palette. ([SkyPlanner][1])

## Primary Colors

| Purpose       | Color      | Hex       |
| ------------- | ---------- | --------- |
| Primary Brand | Deep Blue  | `#1E40AF` |
| Secondary     | Royal Blue | `#2563EB` |
| Accent        | Cyan       | `#06B6D4` |
| Success       | Emerald    | `#10B981` |
| Warning       | Amber      | `#F59E0B` |
| Error         | Red        | `#EF4444` |

---

## Neutral Palette

| Usage          | Hex       |
| -------------- | --------- |
| Background     | `#F8FAFC` |
| Surface        | `#FFFFFF` |
| Border         | `#E2E8F0` |
| Text Primary   | `#0F172A` |
| Text Secondary | `#475569` |
| Disabled       | `#94A3B8` |

---

## Dark Mode

| Usage      | Hex       |
| ---------- | --------- |
| Background | `#020617` |
| Surface    | `#0F172A` |
| Card       | `#1E293B` |
| Border     | `#334155` |
| Text       | `#F8FAFC` |

---

# 4. Typography

Enterprise SaaS products use highly legible sans-serif fonts with strong hierarchy. ([SkyPlanner][1])

## Font Family

```css
font-family: "Inter", sans-serif;
```

Fallback:

```css
font-family: "Inter", "Segoe UI", sans-serif;
```

---

## Scale

### Hero

```txt
56px / Bold / -2%
```

### H1

```txt
40px / Bold
```

### H2

```txt
32px / SemiBold
```

### H3

```txt
24px / SemiBold
```

### Body Large

```txt
18px / Regular
```

### Body

```txt
16px / Regular
```

### Caption

```txt
14px / Medium
```

---

# 5. Layout System

Use a **12-column responsive grid**.

```txt
Desktop : 1440px
Tablet  : 768px
Mobile  : 375px
```

Container width:

```txt
1280px
```

Spacing scale:

```txt
4
8
12
16
24
32
48
64
96
```

Large whitespace between sections similar to modern SaaS sites. ([SkyPlanner][1])

---

# 6. Landing Page Structure

## Section 1 — Hero

### Left

```txt
Headline
Subheadline
CTA Buttons
Trust badges
```

### Right

Interactive product dashboard preview.

Headline:

# AI-Powered Production Scheduling for Modern Factories

Subheadline:

Optimize schedules, minimize delays, and maximize machine utilization in seconds.

Buttons:

```txt
Start Free Trial
Book Demo
```

Background:

```txt
Soft gradient
Blue → Cyan
```

---

## Section 2 — Trusted By

Company logos.

```txt
Bosch
Siemens
Tata Steel
L&T
Mahindra
```

---

## Section 3 — Problem → Solution

Left:

Manufacturing challenges.

Right:

How ShopFloorScheduler solves them.

Use icon cards.

---

## Section 4 — Features Grid

Cards:

```txt
AI Scheduling
Gantt Visualization
Dynamic Rescheduling
Machine Constraints
Performance Analytics
Scenario Simulation
```

3×2 grid.

---

## Section 5 — Dashboard Showcase

Large product screenshots.

Tabs:

```txt
Scheduling
Analytics
Simulation
Reports
```

---

## Section 6 — How It Works

Timeline component.

```txt
1 Upload Jobs
2 Select Algorithm
3 Optimize Schedule
4 Execute Production
```

---

## Section 7 — KPI Metrics

Animated statistics.

```txt
30% Faster Planning
25% Less Downtime
20% Higher Utilization
70% Less Manual Work
```

---

## Section 8 — Testimonials

Enterprise cards.

```txt
Avatar
Quote
Company
Role
```

---

## Section 9 — CTA

Large section.

```txt
Ready to Transform Production Planning?
```

Buttons:

```txt
Start Free Trial
Schedule Demo
```

---

# 7. Component Library

## Buttons

### Primary

```txt
Background: #2563EB
Text: White
Radius: 12px
Height: 48px
```

Hover:

```txt
Scale 1.02
Shadow increase
```

---

### Secondary

```txt
Border: 1px solid #CBD5E1
Background: White
```

---

# Cards

```txt
Radius: 16px
Padding: 24px
Border: #E2E8F0
```

Shadow:

```css
0 1px 2px rgba(0,0,0,0.04)
0 8px 24px rgba(0,0,0,0.06)
```

---

# Tables

Features:

* Sticky headers
* Search
* Filter
* Pagination
* Export

---

# Forms

Style:

```txt
Height: 48px
Radius: 12px
Border: #CBD5E1
```

Focus:

```txt
2px Blue Ring
```

---

# Badges

Examples:

```txt
Running
Completed
Delayed
Critical
Optimized
```

---

# 8. Dashboard Layout

```txt
┌──────────────────────────┐
│ Top Navigation           │
├──────┬───────────────────┤
│ Side │ Main Content      │
│ Nav  │                   │
│      │ KPI Cards         │
│      │                   │
│      │ Gantt Timeline    │
│      │                   │
│      │ Charts            │
│      │                   │
│      │ Job Table         │
└──────┴───────────────────┘
```

---

# 9. Key Dashboard Screens

### Dashboard

* KPI cards
* Machine utilization chart
* Production status
* Recent schedules

### Scheduling Workspace

* Gantt timeline
* Job queue
* Machine list

### Optimization Screen

* Algorithm selector
* Parameters panel
* Results comparison

### Analytics

* Makespan trends
* Tardiness analysis
* Utilization heatmap

### Simulation

* What-if scenarios
* Side-by-side comparison

---

# 10. Animation Guidelines

Use subtle motion only.

Duration:

```txt
200–300ms
```

Effects:

```txt
Fade
Slide
Scale
```

Avoid:

```txt
Bounce
Heavy parallax
Flashy transitions
```

---

# 11. Suggested Tech Stack

Frontend:

* Next.js
* TypeScript
* Tailwind CSS
* Framer Motion

Charts:

* Recharts
* D3.js

UI Library:

* shadcn/ui

Icons:

* Lucide Icons

Tables:

* TanStack Table

Timeline:

* vis-timeline / react-calendar-timeline

---

# 12. Overall Visual Keywords

```txt
Enterprise
Industrial
Minimal
Professional
Data-Driven
AI-Powered
Clean
Modern SaaS
Trustworthy
Efficient
```

