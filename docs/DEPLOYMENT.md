# ShopFloorScheduler — Production Deployment Guide

This guide details how to deploy **ShopFloorScheduler** (FastAPI Backend + Next.js Frontend + PostgreSQL + Redis) to production with **zero computational load on your local PC/laptop**.

---

## 🎯 Recommended Deployment Architecture

To ensure **zero load on your local machine** and hassle-free automated deployments, we recommend the **Managed Cloud Platform Setup**:

```
 ┌───────────────────────────┐         ┌───────────────────────────┐
 │   Vercel (Frontend)       │         │    Render (Backend)       │
 │   Next.js (React / TS)    │ ──────> │    FastAPI + Uvicorn      │
 │   https://frontend.app    │  HTTPS  │    https://backend.app    │
 └───────────────────────────┘         └─────────────┬─────────────┘
                                                     │
                                      ┌──────────────┴──────────────┐
                                      ▼                             ▼
                        ┌───────────────────────────┐ ┌───────────────────────────┐
                        │   Neon.tech / Render      │ │   Upstash / Render        │
                        │   PostgreSQL Database     │ │   Redis Cache & Broker    │
                        └───────────────────────────┘ └───────────────────────────┘
```

### Why this setup?
1. **Zero PC/Laptop Load**: Build processes, container hosting, database execution, and web serving happen 100% in cloud server datacenters.
2. **Free / Low Cost**: Vercel, Render, Neon, and Upstash offer generous free tiers.
3. **Automated CI/CD**: Pushing changes to your `main` branch on GitHub automatically builds and deploys both frontend and backend.
4. **SSL / HTTPS Included**: Automated SSL certificates for free.

---

## 🚀 Step-by-Step Deployment Instructions

### Prerequisites
1. A **GitHub** account containing your `ShopFloorScheduler` code repository.
2. Accounts on:
   - [Vercel](https://vercel.com) (for Frontend)
   - [Render](https://render.com) (for Backend & Workers)
   - [Neon.tech](https://neon.tech) or Render Postgres (for Database)
   - [Upstash](https://upstash.com) or Render Redis (for Redis Cache & Celery)

---

### Step 1: Provision Managed Database & Redis

#### A. PostgreSQL Database (Neon.tech or Render)
1. Sign up on [Neon.tech](https://neon.tech) and create a new project named `shopfloor-db`.
2. Copy the **Connection String** (e.g. `postgresql://alex:password@ep-cool-name-123456.us-east-2.aws.neon.tech/shopfloor_db?sslmode=require`).

#### B. Redis Instance (Upstash or Render)
1. Sign up on [Upstash](https://upstash.com) and create a Redis database.
2. Copy the **Redis URL** (e.g. `rediss://default:password@us1-cool-redis-12345.upstash.io:6379`).

---

### Step 2: Deploy FastAPI Backend on Render

1. Log into your [Render Dashboard](https://dashboard.render.com/) and click **New +** -> **Web Service**.
2. Connect your **GitHub repository** (`ShopFloorScheduler`).
3. Set configuration details:
   - **Name**: `shopfloor-backend`
   - **Region**: Choose closest to your target audience (e.g., Oregon / Frankfurt / Singapore)
   - **Branch**: `main`
   - **Root Directory**: `.` (leave default)
   - **Runtime**: **Docker** (Render auto-detects `Dockerfile`)
4. Add **Environment Variables**:
   | Key | Value / Example |
   | --- | --- |
   | `ENVIRONMENT` | `production` |
   | `DATABASE_URL` | `postgresql://alex:password@ep-cool-name.neon.tech/shopfloor_db?sslmode=require` |
   | `REDIS_URL` | `rediss://default:password@us1-cool-redis.upstash.io:6379` |
   | `CELERY_BROKER_URL` | `rediss://default:password@us1-cool-redis.upstash.io:6379` |
   | `CELERY_RESULT_BACKEND` | `rediss://default:password@us1-cool-redis.upstash.io:6379` |
   | `JWT_SECRET_KEY` | *(Generate a random 64-char string)* |
   | `ALLOWED_ORIGINS` | `https://shopfloor-scheduler.vercel.app` |
5. Click **Create Web Service**.
6. Render will automatically build your Docker container and execute database migrations (`alembic upgrade head`).
7. Copy your assigned backend URL: `https://shopfloor-backend.onrender.com`.

---

### Step 3: Deploy Next.js Frontend on Vercel

1. Log into [Vercel](https://vercel.com) and click **Add New Project**.
2. Import your GitHub repository.
3. In **Framework Preset**, select **Next.js**.
4. Set **Root Directory** to `frontend`.
5. Under **Environment Variables**, add:
   | Key | Value |
   | --- | --- |
   | `NEXT_PUBLIC_API_URL` | `https://shopfloor-backend.onrender.com` |
6. Click **Deploy**.
7. Vercel will build the frontend and assign a live URL (e.g., `https://shopfloor-scheduler.vercel.app`).

---

### Step 4: Verify Deployment

1. Open `https://shopfloor-scheduler.vercel.app` in your web browser.
2. Sign in or register a new user account.
3. Test creating a schedule, running GA/RL optimizations, viewing Gantt charts, and testing real-time WebSocket progress updates.

---

## 🛠️ Alternative: Deployment on a Single VPS (DigitalOcean / AWS / Hetzner)

If you prefer deploying the entire stack on a single server, you can use your existing `docker-compose.yml`:

```bash
# 1. SSH into your cloud server (Ubuntu 22.04 / 24.04 LTS)
ssh ubuntu@<YOUR_SERVER_IP>

# 2. Clone the repository
git clone https://github.com/your-username/ShopFloorScheduler.git
cd ShopFloorScheduler

# 3. Create production .env file
cp .env.example .env
nano .env

# 4. Launch all services in background
docker compose up -d --build
```

You can then put **Nginx** or **Caddy** in front of port 3000 and 8000 with Let's Encrypt SSL:
```bash
sudo apt install caddy
# Add domain routing in /etc/caddy/Caddyfile:
# your-domain.com {
#     reverse_proxy localhost:3000
# }
# api.your-domain.com {
#     reverse_proxy localhost:8000
# }
```

---

## 🔐 Production Checklist

- [ ] `ENVIRONMENT=production` set on backend.
- [ ] Strong `JWT_SECRET_KEY` configured.
- [ ] Production database passwords updated and secured.
- [ ] `ALLOWED_ORIGINS` accurately restricted to the frontend production URL.
- [ ] WebSockets tested over secure `wss://`.
