# Nigerian Jobs API

A paid REST API that delivers live Nigerian job listings scraped from Jobberman.
Pay once via Paystack, get a JWT token, query real job data filtered by location
and paginated however you need it.

Built on top of the [Nigerian Job Intelligence](https://github.com/exceliyoha53/nigerian-job-intelligence)
scraper — which fills the database automatically every 6 hours.

---

## How it works
```
Jobberman.com
     ↓
Playwright scraper (runs every 6 hours)
     ↓
PostgreSQL vault — 72+ jobs and growing
     ↓
This API — auth, paywall, pagination, filtering
     ↓
Paying users getting clean job data
```

The scraper and the API never talk to each other directly.
They share the same PostgreSQL database. One writes, one reads.

---

## Endpoints
```
POST /auth/register       → create an account
POST /auth/login          → get your JWT token
GET  /auth/me             → check your profile

POST /payments/subscribe  → get a Paystack checkout URL
GET  /payments/verify     → confirm payment, unlock access

GET  /jobs                → paginated job listings (subscription required)
GET  /jobs?location=Lagos → filter by any city
GET  /jobs?page=2         → navigate pages

GET  /health              → API status
GET  /docs                → interactive Swagger documentation
```

---

## Auth flow

Register → Login → copy your token → click Authorize in /docs → make requests.

Every protected endpoint checks your JWT automatically.
No valid token, no data. No active subscription, no data.

---

## Stack

- `FastAPI` — async Python web framework, auto-generates Swagger docs
- `PostgreSQL` + `psycopg2` — production database with connection pooling
- `passlib` + `bcrypt` — password hashing, one-way, irreversible
- `python-jose` — JWT token generation and verification
- `Paystack` — Nigerian-native payment processing
- `httpx` — async HTTP client for Paystack API calls
- `pydantic` — request and response validation

---

## One thing that broke

Swagger's Authorize button sends credentials as form data — not JSON.
My login endpoint expected JSON. Every authorize attempt returned 422 Unprocessable Entity.

Fix: switched to `OAuth2PasswordRequestForm` — the proper OAuth2 standard.
Now Swagger handles auth correctly and the endpoint works for both
Swagger UI and real API clients.

---

## Setup
```bash
git clone https://github.com/YOUR_USERNAME/nigerian-jobs-api
cd nigerian-jobs-api
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file:
```
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/nigerian_jobs
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
PAYSTACK_SECRET_KEY=your-paystack-test-key
```

Run:
```bash
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` and the full API is there.

---

## What's next

Month 4: AI agents. RAG pipeline, tool calling, LangGraph.
The jobs vault becomes the knowledge base for an AI customer support agent.