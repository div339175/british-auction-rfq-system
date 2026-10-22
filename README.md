# British Auction in RFQ System

A full-stack, enterprise-grade Request for Quotation (RFQ) platform implementing **British Auction** mechanics with autonomous anti-sniping dynamic bid extensions, hard forced close deadlines, and supplier ranking leaderboards.

---

## 1. Key Features

- **British Auction Mechanics**: Prevents last-minute bid sniping by automatically extending the closing time when qualifying activity occurs within the trigger window ($X$ minutes).
- **Hard Forced Close Cap**: Guarantees auction determinism. Extensions are strictly clamped to `forced_bid_close_time`, beyond which no bid may extend or be submitted.
- **Configurable Extension Triggers**:
  - `BID_RECEIVED`: Any valid quote inside the trigger window triggers an extension.
  - `RANK_CHANGE`: Any shift in supplier ranking ($L1, L2, \dots$) triggers an extension.
  - `L1_CHANGE`: Only bids displacing the lowest bidder ($L1$) trigger an extension.
- **Dynamic Moving Trigger Window**: Moving close times automatically shift the trigger window forward.
- **Pessimistic Concurrency Control**: Uses PostgreSQL row-level locks (`SELECT ... FOR UPDATE`) to prevent race conditions, lost updates, or duplicate extensions under simultaneous bids.
- **Pure Domain Engine**: The core auction evaluation logic (`BritishAuctionEngine`) is decoupled from the database, allowing lightning-fast unit testing of boundary conditions.
- **Live Leaderboard & Audit Trail**: Chronological activity log records quote submissions, extensions, reasons, and state transitions.
- **Background Expiration**: Hybrid status reconciler backed by Celery + Redis and on-demand passive checks.

---

## 2. System Architecture

```mermaid
flowchart TD
    subgraph Frontend["React 18 + Vite + TypeScript"]
        ListingPage["Auction Listing Page\n(Status, L1, Timers)"]
        DetailPage["Auction Detail Page\n(Rankings L1..Ln, Quote Form, Logs)"]
        Clock["Authoritative Server Countdown"]
    end

    subgraph Backend["FastAPI Application"]
        Routers["API Routers (/rfqs, /quotes, /logs)"]
        RFQService["RFQService (Lifecycle & Reconciler)"]
        QuoteService["QuoteService (Transaction & Row Lock)"]
        CoreEngine["BritishAuctionEngine (Pure Domain Logic)"]
    end

    subgraph Storage["Datastore (PostgreSQL / SQLite)"]
        DB_RFQ[("rfqs")]
        DB_Quote[("quotes")]
        DB_Log[("auction_activity_logs")]
    end

    subgraph Workers["Background Workers"]
        Redis[("Redis Broker")]
        CeleryWorker["Celery Worker"]
        CeleryBeat["Celery Beat (Every 5s)"]
    end

    ListingPage -->|GET /api/v1/rfqs| Routers
    DetailPage -->|POST /api/v1/rfqs/{id}/quotes| Routers
    Routers --> RFQService
    Routers --> QuoteService
    QuoteService -->|1. Row Lock| DB_RFQ
    QuoteService -->|2. Evaluate| CoreEngine
    QuoteService -->|3. Persist Quote & Extension| DB_Quote
    QuoteService -->|4. Audit Log| DB_Log
    CeleryBeat --> Redis --> CeleryWorker --> RFQService
```

For full system diagrams and component breakdowns, see [architecture-hld.md](docs/architecture-hld.md).

---

## 3. Tech Stack

- **Backend**: FastAPI, Python 3.11+, Pydantic v2, SQLAlchemy 2.0
- **Database**: PostgreSQL 16 (production/Docker) / SQLite with WAL mode (local testing)
- **Background Workers**: Celery 5.3+, Redis 7
- **Frontend**: React 18, TypeScript, Vite, TailwindCSS, Lucide Icons
- **Testing**: Pytest, Pytest-Asyncio, HTTPX

---

## 4. Quick Start Guide

### Option A: Running Locally (Fastest)

#### 1. Backend Setup
```bash
# Navigate to project root
cd gocomet

# Create and activate Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt

# Run database migrations / start backend
cd backend
PYTHONPATH=. uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
The API is now running at `http://localhost:8000`.  
Swagger UI documentation is available at `http://localhost:8000/docs`.

#### 2. Frontend Setup
```bash
# In a new terminal tab
cd gocomet/frontend

# Install node dependencies
npm install

# Start Vite development server
npm run dev
```
Open `http://localhost:5173` in your browser.

---

### Option B: Running with Docker Compose (Full Stack)

To run the complete production environment (PostgreSQL 16, Redis 7, FastAPI backend, Celery worker, Celery beat, and Nginx frontend):

```bash
docker compose up --build
```

- **Frontend Application**: `http://localhost:3000`
- **Backend API**: `http://localhost:8000`
- **Interactive API Docs**: `http://localhost:8000/docs`

---

## 5. Running the Test Suite

The test suite covers unit tests for the pure auction engine, boundary conditions, concurrent bid ingestion, API endpoints, background tasks, and full end-to-end auction lifecycles:

```bash
source venv/bin/activate
cd backend
PYTHONPATH=. pytest tests/ -v
```

### Test Coverage Highlights:
- `test_auction_engine.py`: 11 unit tests covering edge cases (exact close time, clamped extensions, rank changes, uncompetitive quotes, tie-breaking).
- `test_concurrency.py`: Concurrent multi-threaded bid submission with row locking.
- `test_e2e_lifecycle.py`: Complete lifecycle test with moving trigger window verification.
- `test_rfq_api.py`: RFQ creation, constraint validations, listing, and details.
- `test_quote_api.py`: Quote submissions, charge calculations, and dynamic extensions.
- `test_tasks.py`: Celery background reconciliation for expired auctions.

---

## 6. API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/rfqs` | Create an RFQ with British Auction parameters |
| `GET` | `/api/v1/rfqs` | List all RFQs with current status and lowest bid |
| `GET` | `/api/v1/rfqs/{id}` | Get RFQ details, supplier leaderboard, quotes, and audit logs |
| `POST` | `/api/v1/rfqs/{id}/quotes` | Submit a quote (evaluates trigger window, rank, and extensions) |
| `GET` | `/api/v1/rfqs/{id}/logs` | Fetch chronological activity logs for an RFQ |
| `GET` | `/health` | System health check |

---

## 7. Documentation Index

- [High-Level Architecture (HLD)](docs/architecture-hld.md): System architecture, Mermaid diagrams, state machines.
- [Database Schema Design](docs/schema-design.md): Entity relationship diagrams, data dictionaries, indexes, and constraints.
- [Architectural Decision Record (ADR)](docs/decisions.md): System design thinking, alternatives, and explicit trade-offs.
- [Debugging Notes & Incidents](docs/debugging-notes.md): Real incident log of edge cases discovered and resolved during development.
- [Requirements Analysis](docs/requirements-analysis.md): Product goals, business rules, and mathematical specifications.
- [Simulated Code Review](docs/simulated-code-review.md): Senior engineer review of design, concurrency, security, and edge cases.
