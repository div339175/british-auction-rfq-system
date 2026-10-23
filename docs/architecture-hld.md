# High-Level Architecture Design (HLD)

## 1. System Overview
The British Auction RFQ System is an enterprise freight procurement platform. It enables buyers to post RFQs with British auction mechanics (reverse auction with dynamic anti-sniping extensions and a hard forced close time limit), and allows carriers to submit competing quotes.

---

## 2. Architecture Diagram

```mermaid
flowchart TD
    subgraph Client["Frontend Client (React + Vite + TypeScript)"]
        UI_List["Auction Listing Page<br/>(Status, L1, Timers)"]
        UI_Detail["Auction Detail Page<br/>(Quotes, Ranking L1..Ln, Form, Logs)"]
        UI_Timer["Authoritative Countdown Timer<br/>(Local sync with Server Clock)"]
    end

    subgraph API_Gateway["FastAPI Application"]
        Router_RFQ["/api/v1/rfqs Router"]
        Router_Quote["/api/v1/quotes Router"]
        Router_Activity["/api/v1/activity-logs Router"]
    end

    subgraph Services["Service Layer"]
        RFQService["RFQService<br/>(Lifecycle, Validation, Fetching)"]
        QuoteService["QuoteService<br/>(Transaction management, Bid placement)"]
    end

    subgraph CoreEngine["Pure Domain Engine (Zero DB Dependencies)"]
        AuctionEngine["BritishAuctionEngine<br/>- Trigger window calculation<br/>- Ranking evaluation (L1..Ln)<br/>- Extension evaluation<br/>- Forced-close clamp"]
    end

    subgraph Storage["Data Tier (PostgreSQL / SQLite)"]
        DB_RFQ[("rfqs<br/>(State, Timestamps, Config)")]
        DB_Quotes[("quotes<br/>(Bids, Breakdown, Validity)")]
        DB_Logs[("auction_activity_logs<br/>(Audit trail, Extensions, Reasons)")]
    end

    subgraph Background["Background Workers & Scheduler"]
        CeleryWorker["Celery Worker<br/>(Auction close tasks)"]
        CeleryBeat["Celery Beat Scheduler<br/>(Periodic status reconciler)"]
        RedisBroker[("Redis Broker & Result Backend")]
    end

    UI_List -->|"HTTP GET /api/v1/rfqs"| Router_RFQ
    UI_Detail -->|"HTTP GET /api/v1/rfqs/:id"| Router_RFQ
    UI_Detail -->|"HTTP POST /api/v1/quotes"| Router_Quote
    
    Router_RFQ --> RFQService
    Router_Quote --> QuoteService
    
    QuoteService -->|"1. Acquire Row Lock"| DB_RFQ
    QuoteService -->|"2. Evaluate Bid & Extension"| AuctionEngine
    QuoteService -->|"3. Save Bid & Update Times"| DB_Quotes
    QuoteService -->|"4. Record Audit Log"| DB_Logs
    
    RFQService --> DB_RFQ
    RFQService --> DB_Quotes
    RFQService --> DB_Logs
    
    CeleryBeat -->|"Push close checks"| RedisBroker
    RedisBroker -->|"Consume tasks"| CeleryWorker
    CeleryWorker -->|"Reconcile expired auctions"| RFQService
```

---

## 3. Component Breakdown

### 3.1 Frontend (React + Vite + TailwindCSS)
- **Role**: Pure presentation layer.
- **Responsibilities**:
  - Render RFQ listing with current status badge (`UPCOMING`, `ACTIVE`, `CLOSED`, `FORCE_CLOSED`), current lowest bid ($L1$), and close times.
  - Render RFQ details with interactive quote submission form, ranked leaderboard ($L1, L2, \dots$), breakdown of freight/origin/destination charges, and complete chronological activity log.
  - Render an accurate countdown timer derived strictly from server-provided `current_bid_close_time`.
  - Polling mechanism (every 3 seconds on active auction details) to display newly submitted bids and extensions without manual refresh.

### 3.2 FastAPI Web Layer
- **Role**: HTTP serialization, input validation, status codes, OpenAPI schema generation.
- **Routers**:
  - `POST /api/v1/rfqs`: Create an RFQ with British Auction parameters.
  - `GET /api/v1/rfqs`: List RFQs with current summary (status, lowest quote, close times).
  - `GET /api/v1/rfqs/{id}`: Detailed RFQ state including quote history, ranked suppliers, and activity logs.
  - `POST /api/v1/rfqs/{id}/quotes`: Submit a quote / bid.
  - `GET /api/v1/rfqs/{id}/logs`: Fetch activity and audit logs for an RFQ.

### 3.3 Service Layer
- **`RFQService`**: Coordinates RFQ creation, validation (e.g. `forced_bid_close_time > bid_close_time`), retrieving active views, and background closure reconciliation.
- **`QuoteService`**: Wraps quote submission in an atomic database transaction. Acquires pessimistic row-level lock on the RFQ, invokes `BritishAuctionEngine`, writes the quote, applies extensions, and writes activity log records.

### 3.4 British Auction Engine (`auction_engine.py`)
- **Role**: Pure domain logic. No ORM models, no SQL, no network calls. Takes data inputs and returns deterministic state transitions.
- **Inputs**:
  - `current_close_time`: `datetime`
  - `forced_close_time`: `datetime`
  - `trigger_window_minutes`: `int` ($X$)
  - `extension_duration_minutes`: `int` ($Y$)
  - `trigger_type`: Enum (`BID_RECEIVED`, `RANK_CHANGE`, `L1_CHANGE`)
  - `current_ranking`: Current list of ranked supplier prices
  - `new_bid`: Carrier and total price
  - `bid_timestamp`: `datetime`
- **Outputs**:
  - `is_valid`: Boolean (whether bid is acceptable)
  - `validation_error`: Optional string reason
  - `new_ranking`: Updated list of ranked suppliers
  - `rank_changed`: Boolean
  - `l1_changed`: Boolean
  - `should_extend`: Boolean
  - `new_close_time`: Updated `datetime`
  - `extension_reason`: Human-readable reason for audit log
  - `is_capped`: Boolean (whether extension hit forced close limit)

### 3.5 Celery & Redis
- **Role**: Periodic background reconciliation.
- **Worker**: Every 5 seconds, Celery Beat runs `reconcile_auction_statuses` task to check for active RFQs whose `current_bid_close_time` or `forced_bid_close_time` has elapsed and updates their status to `CLOSED` or `FORCE_CLOSED`.

---

## 4. Auction State Machine

```mermaid
stateDiagram-v2
    [*] --> UPCOMING : RFQ Created (start_time in future)
    [*] --> ACTIVE : RFQ Created (start_time in past and before close_time)
    UPCOMING --> ACTIVE : bid_start_time reached
    ACTIVE --> ACTIVE : Bid received outside trigger window (no extension)
    ACTIVE --> ACTIVE : Qualifying bid in trigger window (extended by Y min)
    ACTIVE --> ACTIVE : Extension capped at forced_bid_close_time
    ACTIVE --> CLOSED : current_bid_close_time reached (normal expiry)
    ACTIVE --> FORCE_CLOSED : forced_bid_close_time reached (hard cap)
    CLOSED --> [*]
    FORCE_CLOSED --> [*]
```
