## Incident 01: Boundary condition in extension clamping calculation

**Date**: 2026-10-22
**Component**: `BritishAuctionEngine` (`app/engine/auction_engine.py`)
**Test**: `test_multiple_extensions_cannot_exceed_forced_close`

### Issue
When `c_time + extension_duration == f_time` (e.g., 18:05 + 5m == 18:10 forced close), the engine marked `is_capped = True` and formatted the message as "clamped to forced close deadline", even though the full 5 minutes was granted without truncation.

### Root Cause
The condition used was `if candidate_close >= f_time` instead of distinguishing between:
1. `candidate_close > f_time`: Candidate strictly exceeded ceiling; truncated to `f_time` (`is_capped = True`).
2. `candidate_close == f_time`: Candidate exactly met ceiling; full extension granted (`is_capped = False`, but next bid cannot extend).
3. `c_time >= f_time`: Already at forced close; no extension possible (`should_extend = False`, `is_capped = True`).

### Fix
Refined comparison to check `candidate_close > f_time` for truncation clamping, while setting `new_close = candidate_close` when `candidate_close <= f_time`.

### Verification
`test_multiple_extensions_cannot_exceed_forced_close` passed with exact verification of full vs clamped extensions.

---

## Incident 02: Moving trigger window behavior after repeated extensions

**Date**: 2026-10-22
**Component**: `QuoteService` & `BritishAuctionEngine`
**Test**: `test_full_british_auction_journey`

### Issue
In the e2e test, three bids were submitted in rapid succession at timestamp $T_0$.
- Initial close was $T_0 + 5\text{m}$, trigger window $X = 10\text{m}$.
- Bid 1 at $T_0$ was inside the window ($T_0 - 5\text{m}$ to $T_0 + 5\text{m}$), extending close to $T_0 + 10\text{m}$.
- Bid 2 at $T_0$ was inside the new window ($T_0$ to $T_0 + 10\text{m}$), extending close to $T_0 + 15\text{m}$.
- Bid 3 at $T_0$ did not trigger an extension, resulting in `extension_count == 2` instead of 3.

### Root Cause
Because each extension moves `bid_close_time` forward, the trigger window $[c\_time - X, c\_time)$ moves forward dynamically.
Once $c\_time$ moved to $T_0 + 15\text{m}$, the new trigger window became $[T_0 + 5\text{m}, T_0 + 15\text{m})$.
A bid placed at $T_0$ is 15 minutes before close, which is outside the last 10 minutes trigger window!
This is mathematically and logically the correct behavior: an extension should only happen when activity occurs close to the active end time, not arbitrarily far in advance.

### Fix
Updated test assertions to verify that Bid 3 correctly ingests, ranks, and updates the leaderboard without inappropriately triggering an extension when outside the newly moved trigger window. Also added verification that a bid placed inside $[T_0 + 5\text{m}, T_0 + 15\text{m})$ successfully triggers the 3rd extension.

---

## Incident 03: `ModuleNotFoundError: No module named 'psycopg'` in Docker Compose

**Date**: 2026-10-22  
**Component**: Docker Compose (`DATABASE_URL`) & SQLAlchemy 2.0 PostgreSQL dialect loader  
**Symptom**: `british_auction_backend`, `british_auction_celery_worker`, and `british_auction_celery_beat` failed on startup with `ModuleNotFoundError: No module named 'psycopg'`.

### Root Cause
1. In SQLAlchemy 2.0, if a connection string uses the generic prefix `postgresql://` without specifying a DBAPI driver, SQLAlchemy's default dialect resolution attempts to import `psycopg` (psycopg version 3) via `sqlalchemy.dialects.postgresql.psycopg`.
2. The initial `backend/requirements.txt` installed `psycopg2-binary` (which provides `psycopg2` via `postgresql+psycopg2://`), not `psycopg` (psycopg 3).
3. `docker-compose.yml` set `DATABASE_URL: postgresql://...` rather than specifying `postgresql+psycopg2://...`.

### Fix
1. Explicitly normalized any `postgresql://` URL in `backend/app/database.py` to `postgresql+psycopg2://` before initializing the SQLAlchemy engine.
2. Updated `docker-compose.yml` to specify `postgresql+psycopg2://postgres:password123@db:5432/british_auction`.
3. Added `psycopg[binary]>=3.1.18` alongside `psycopg2-binary>=2.9.9` in `backend/requirements.txt` so both psycopg v2 and v3 drivers are available in any environment.



