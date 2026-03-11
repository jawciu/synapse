# Free Hosting Research for Synapse

> Research date: March 2026
> Context: Moving off Render (sleep after 15min, cold starts, POST requests don't wake it)

## TL;DR

**Best option: Oracle Cloud Always Free + Cloudflare Pages**

Run SurrealDB + FastAPI + Telegram bot on a free Oracle ARM VM (4 cores, 24GB RAM).
Serve React frontend from Cloudflare Pages (unlimited bandwidth).

---

## The SurrealDB Constraint

No managed free hosting exists for SurrealDB. This rules out most PaaS platforms
(Koyeb, Railway, Cloud Run etc.) unless we switch databases. Self-hosting on a VM
is the only viable free path that keeps our current stack.

---

## Recommended Setup

### Oracle Cloud Always Free (Backend + DB)

| Resource | Amount |
|----------|--------|
| ARM (Ampere A1) cores | 4 OCPUs |
| RAM | 24 GB |
| Block storage | 200 GB |
| Egress | 10 TB/month |
| AMD micro instances | 2x (1/8 OCPU, 1 GB RAM) |
| Autonomous Databases | 2 instances |

- **No expiry**, no credit card charges within limits, commercial use allowed
- Runs 24/7, no cold starts, no sleep
- Docker Compose to run: SurrealDB + FastAPI + Telegram bot

**Gotchas:**
- ARM instances hard to provision in popular regions ("Out of Host Capacity")
- Enable Pay-As-You-Go to unlock ARM (won't be charged within free limits)
- You manage the server yourself (updates, security, Docker)
- Tip: pair with Coolify (open-source PaaS) for Heroku-like DX

### Cloudflare Pages (Frontend)

- Unlimited sites, **unlimited bandwidth**, unlimited requests
- 500 builds/month, 100 custom domains
- No credit card required
- Global CDN + DDoS protection

---

## Platforms That Lost Free Tiers (Avoid)

| Platform | Status |
|----------|--------|
| **Railway** | No free tier. One-time $5 trial credit, expires in 30 days |
| **Fly.io** | No free tier for new users. Legacy hobby users grandfathered |
| **PlanetScale** | Killed free tier April 2024. Scaler Pro starts at $34/mo |
| **Heroku** | Killed free tier November 2022 |
| **Render** | Free tier exists but: 15min sleep, ~25s cold starts, POST doesn't wake |

## Other Options Considered

### Koyeb (Runner-up for backend)
- 1 free web service (0.1 vCPU, 512 MB RAM) + 1 free Postgres DB
- No credit card, no expiry
- **Problem:** 512 MB too tight for SurrealDB + FastAPI, only 1 service allowed
- Acquired by Mistral AI in Feb 2026 - future uncertain

### Google Cloud Run
- 2M requests/mo free, 180K vCPU-seconds
- **Problem:** Serverless = scales to zero = can't persist SurrealDB
- Would require switching to managed Postgres (Neon/Supabase)

### Vercel / Netlify (Frontend alternatives)
- Both offer ~100 GB bandwidth free
- Vercel: **prohibits commercial use** on free tier
- Netlify: credit-based system since Sept 2025, sites pause when credits run out
- Neither beats Cloudflare Pages for pure static hosting

### Neon (If we ever switch from SurrealDB)
- Best free Postgres: 0.5 GB storage, branching, scale-to-zero
- 100 compute-hours/month (can't run 24/7)
- Good option if we ever drop SurrealDB for Postgres

---

## Action Plan

1. Sign up for Oracle Cloud (oracle.com/cloud/free)
2. Provision ARM VM (4 OCPU, 24 GB RAM) - may need to try multiple regions
3. Set up Docker Compose with: SurrealDB, FastAPI backend, Telegram bot
4. Deploy React frontend to Cloudflare Pages
5. Optional: Set up Cloudflare Tunnel for nice domain → Oracle VM routing
6. Optional: Install Coolify on Oracle VM for easier deployments
