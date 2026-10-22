# Architectural Decision Record (ADR) & Design Decisions

This document captures the system design thinking, trade-offs, and rationale behind the British Auction RFQ Engine.

---

## ADR 01: Core Backend Framework — FastAPI (Python 3.11+)

### Problem
We need an API framework with native async support, strict data validation, automatic OpenAPI specification generation, and clean dependency injection.

### Decision
Use **FastAPI** with **Pydantic v2**.

### Why?
- Automatic OpenAPI documentation at `/docs` simplifies frontend and third-party integration.
- Pydantic v2 provides high-performance schema validation, eliminating manual deserialization and validation boilerplate.
- Native dependency injection simplifies testing by allowing easy swapping of database sessions.

### Alternative
- **Django / DRF**: Heavier batteries-included framework; included ORM migrations and admin panel are unnecessary overhead for this focused microservice.
- **Flask**: Lightweight, but requires extensive third-party plugins for OpenAPI, type validation, and async tasks.

### Trade-off
FastAPI does not prescribe an opinionated project layout, requiring deliberate architectural discipline in organizing service layers and domain logic.

---

## ADR 02: Relational Database & ORM — PostgreSQL + SQLAlchemy 2.0

### Problem
Reverse auction bidding requires strict relational consistency, foreign keys, decimal precision on monetary charges, and pessimistic row locking to prevent race conditions during concurrent bid arrivals.

### Decision
Use **PostgreSQL 16** with **SQLAlchemy 2.0** as the primary datastore, while supporting SQLite with WAL mode for local zero-dependency testing.

### Why?
- Relational schema guarantees strict constraints: `forced_bid_close_time > bid_close_time`, `bid_close_time > bid_start_time`, and non-negative charges.
- Precise financial types (`Numeric(12, 2)`) prevent IEEE 754 floating-point rounding errors.
- `SELECT ... FOR UPDATE` row locking provides serialized transaction safety for concurrent bids.

### Alternative
- **MongoDB / NoSQL**: Schema flexibility is unneeded because RFQs and quotes have strictly structured formats. Distributed locking without multi-document ACID transactions introduces unnecessary operational risk.

### Trade-off
Requires managing relational database migrations upfront.

---

## ADR 03: Layered Architecture Pattern

### Problem
Embedding auction business logic directly into route functions tightly couples domain logic to HTTP frameworks, making unit testing slow and brittle.

### Decision
Strict 4-tier separation:
```
API Layer (FastAPI Routers)
       ↓
Service Layer (RFQService, QuoteService)
       ↓
Auction Engine (Pure Domain Logic & State Evaluator)
       ↓
Repository & Database Layer (SQLAlchemy Models)
```

### Why?
- **BritishAuctionEngine** is completely decoupled from SQLAlchemy, HTTP requests, or databases. It accepts pure data values and returns deterministic evaluation results.
- Unit testing domain edge cases (boundary timestamps, clamped extensions, rank shifts) executes in milliseconds without spawning database connections or HTTP servers.
- The **Service Layer** coordinates database sessions, row locks, audit log persistence, and background tasks.

### Alternative
- Fat controllers / routes: Rapid to write initially, but leads to duplicate logic, difficult unit tests, and race conditions.

### Trade-off
Slightly higher file count and data transfer objects (DTOs), but vastly superior maintainability and testability.

---

## ADR 04: Concurrency Control for Simultaneous Bid Ingestion

### Problem
If Supplier A (₹95,000) and Supplier B (₹94,000) submit bids at the exact same millisecond:
1. Both could read the same unextended close time.
2. Both could attempt to extend the auction by 5 minutes independently.
3. Without concurrency control, the close time could erroneously extend twice or result in a lost update, and rank order could be corrupted.

### Decision
Apply **Pessimistic Row Locking (`SELECT ... FOR UPDATE`)** on the `rfqs` row at the start of `QuoteService.submit_quote`:
```sql
SELECT * FROM rfqs WHERE id = :rfq_id FOR UPDATE;
```

### Why?
- Database-level row locking serializes transactions modifying the same auction.
- The second transaction blocks until the first commits, ensuring it reads the updated `bid_close_time`, the updated supplier rankings, and the incremented `extension_count`.
- Fails safely: if the first transaction fails or DB connection drops, the row lock is released immediately.

### Alternative
- **Optimistic Locking (`version` column)**: Would reject the second concurrent bid with a conflict error (`409 Conflict`), forcing the supplier to retry. In a competitive auction, rejecting a supplier's quote due to an internal race condition causes poor user experience.
- **Distributed Redis Lock (Redlock)**: Adds distributed system complexity, clock drift concerns, and potential TTL expiration before completion. PostgreSQL row locking is already ACID-compliant and native to our transactional boundary.

### Trade-off
Simultaneous bids on the *same* RFQ are processed sequentially in queue order rather than in parallel. However, since the database transaction takes < 5ms, throughput easily handles dozens of bids per second per RFQ.

---

## ADR 05: How Auction Extensions and Trigger Windows Work

### Problem
The trigger window ($X$ minutes) and extension duration ($Y$ minutes) must prevent last-second bid sniping while ensuring the auction deterministically terminates.

### Decision
1. **Dynamic Trigger Window Calculation**:
   - The trigger window is calculated relative to the **current active close time** (`current_bid_close_time`), NOT the original close time.
   - Trigger Start = $current\_bid\_close\_time - X\text{ minutes}$.
   - Trigger End = $current\_bid\_close\_time$.
   - A bid is in the trigger window if: $trigger\_start \le bid\_time < current\_bid\_close\_time$.
2. **Moving Window After Extension**:
   - When an extension occurs, `bid_close_time` moves forward by $Y$ minutes.
   - The trigger window automatically shifts forward with the new close time.
   - Any bid submitted subsequently must fall within the *new* trigger window to cause an additional extension.
3. **Trigger Modes**:
   - `BID_RECEIVED`: Any valid bid within the window extends the auction.
   - `RANK_CHANGE`: Bids that alter the relative order of suppliers ($L1, L2, \dots$) extend the auction.
   - `L1_CHANGE`: Only bids that displace the current lowest bidder ($L1$) extend the auction.

### Alternative
- Static trigger window based on original close time: Fails to prevent sniping during subsequent extensions.

---

## ADR 06: How Forced Close is Enforced

### Problem
Auctions cannot extend indefinitely; buyers need certainty that bidding terminates by an absolute deadline.

### Decision
Enforce a hard `forced_bid_close_time` ceiling at three independent layers:
1. **Database Check Constraint**: `forced_bid_close_time > bid_close_time`.
2. **Auction Engine Clamping**:
   - If $current\_close\_time + Y > forced\_bid\_close\_time$, the new close time is capped strictly at `forced_bid_close_time`.
   - If $current\_close\_time == forced\_bid\_close\_time$, further extensions are completely prohibited (`should_extend = False`).
3. **Submission Gatekeeper**: Any bid submitted at or after `forced_bid_close_time` is rejected with `400 Bad Request`.

---

## ADR 07: How Supplier Rankings are Calculated

### Problem
Carriers may submit multiple revised quotes to lower their prices. How should supplier ranks ($L1, L2, L3, \dots$) be determined?

### Decision
1. Each carrier's **lowest total price** (`freight + origin + destination`) represents their active standing in the auction.
2. Suppliers are sorted ascending by total price (reverse auction: lower is better).
3. **Tiebreaker**: If two suppliers offer the exact same price, the supplier who submitted earlier receives the better (numerically lower) rank.
4. Ranks are labeled $L1$ (1st place / lowest price), $L2$ (2nd place), $L3$ (3rd place), etc.
5. In addition, each historical quote records the `rank_at_submission` snapshot for auditability.

---

## ADR 08: Background Auction Monitoring — Celery + Redis vs Passive Reconciler

### Problem
If no bids are submitted near the end of an auction, the auction must still transition to `CLOSED` or `FORCE_CLOSED`. Relying exclusively on HTTP requests can leave an auction in `ACTIVE` state indefinitely if no one visits the page.

### Decision
Implement a **hybrid dual-layer strategy**:
1. **Active Celery Worker + Celery Beat**: A periodic Celery Beat task runs every 5 seconds, scanning open auctions and reconciling expired ones.
2. **Passive Reconciler**: Whenever an RFQ is read or written via API, `RFQService.reconcile_rfq_status()` checks the current timestamp against close times and updates the database immediately.

### Why?
- Guarantees zero stale states even in local test environments where Celery might not be running.
- In production, Celery Beat ensures auctions close reliably in the background without user intervention.

### Trade-off
Requires Redis and Celery worker containers in production deployment.

---

## ADR 09: Real-Time Updates — Frequent Client Polling vs WebSockets

### Problem
The frontend needs to reflect new bids, ranking shifts, and close time extensions in near real-time.

### Decision
Use **HTTP Short Polling (every 3 seconds)** when viewing an active auction, combined with optimistic instant local updates upon quote submission.

### Why?
- Logistics RFQs typically receive bids spaced seconds or minutes apart, not hundreds of frames per second. A 3-second polling interval creates negligible server load.
- Avoids the operational fragility, stateful connection management, and reconnection heartbeat handling of WebSockets or SSE.
- Fully compatible with standard HTTP load balancers and serverless gateways without sticky sessions.

### Alternative
- WebSockets: Better for high-frequency sub-second trading platforms, but overkill and fragile for enterprise procurement RFQs.

### Trade-off
Up to 3-second latency for passive viewers to see a competitor's bid.

---

## ADR 10: Explicit Assumptions Made

1. **Reverse Auction Mechanics**: Freight procurement is a reverse auction: buyers want lowest cost, so suppliers compete downwards ($L1$ is minimum price).
2. **Quote Price Components**: Total price is strictly `freight_charges + origin_charges + destination_charges`. All charges must be $\ge 0$ and the sum must be $> 0$.
3. **Single Active Quote Per Carrier**: A carrier can place multiple bids over time, but subsequent bids must be strictly lower than their own prior lowest bid to be accepted.
4. **Timezone Standardization**: All timestamps stored and calculated in UTC (`TIMESTAMPTZ`), with local browser timezone formatting on the frontend.
