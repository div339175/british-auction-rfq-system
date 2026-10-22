# Phase 1: Requirements Analysis & Specification

## 1. Problem Overview
In freight and logistics procurement, buyers issue Requests for Quotation (RFQs) to multiple carriers/suppliers. In standard static RFQs, suppliers often wait until the last seconds to submit their bids ("sniping"), preventing true market price discovery and fair competition.
The British Auction mechanism counters this by:
1. Allowing suppliers to submit quotes openly and iteratively lower prices.
2. Automatically extending the bid close time by $Y$ minutes if qualifying bidding activity occurs within the final $X$ minutes (trigger window).
3. Enforcing a hard "Forced Close Time" ceiling to guarantee that the auction terminates deterministically.

---

## 2. Detailed Functional Requirements

### 2.1 RFQ Management
- **Creation Fields**:
  - `rfq_name`: Unique or human-readable title.
  - `reference_id`: Unique reference code (e.g. `RFQ-2026-001`).
  - `bid_start_time`: Timestamp when bidding opens.
  - `bid_close_time`: Initial timestamp when bidding closes.
  - `forced_bid_close_time`: Absolute deadline beyond which no extension can push the closing time. Must be strictly $> bid\_close\_time$.
  - `pickup_service_date`: Expected date/time of freight service/pickup. Must be $> bid\_start\_time$.
  - `british_auction_enabled`: Boolean (defaults to True).
  - British Auction Config:
    - `trigger_window_minutes` ($X$): Window before close time where events trigger an extension (must be $> 0$).
    - `extension_duration_minutes` ($Y$): Duration added to the current close time upon trigger (must be $> 0$).
    - `extension_trigger_type`: Enum:
      - `BID_RECEIVED`: Any valid bid within the trigger window triggers extension.
      - `RANK_CHANGE`: Any shift in supplier ranking ($L1, L2, \dots$) triggers extension.
      - `L1_CHANGE`: Only a change of the lowest bidder ($L1$) triggers extension.

### 2.2 Quote / Bid Submission
- **Fields**:
  - `rfq_id`: Foreign key reference to RFQ.
  - `carrier_name`: Supplier or carrier identifier.
  - `freight_charges`: Non-negative decimal.
  - `origin_charges`: Non-negative decimal.
  - `destination_charges`: Non-negative decimal.
  - `total_price`: Calculated sum (`freight + origin + destination`).
  - `transit_days` / `transit_time`: Delivery duration commitment.
  - `quote_validity`: Expiration timestamp of the quote (must be $\ge bid\_close\_time$).
  - `submitted_at`: Timestamp of submission.

### 2.3 Ranking Rules
- Bids are ranked in ascending order of `total_price` (Reverse auction: lower is better).
- Tiebreaker: Earlier `submitted_at` gets the better (lower numerical) rank.
- A carrier may submit multiple bids over time. For supplier ranking, each carrier's best (lowest total price) active quote determines their current rank ($L1, L2, L3, \dots$).
- Rank labels:
  - $L1$: Lowest bidder (1st place)
  - $L2$: 2nd lowest bidder
  - $Ln$: $n$-th lowest bidder

### 2.4 Extension Engine Logic
1. **Trigger Window Calculation**:
   - Trigger start = $current\_bid\_close\_time - X\text{ minutes}$.
   - Trigger end = $current\_bid\_close\_time$.
   - A bid is in the trigger window if: $trigger\_start \le bid\_timestamp < current\_bid\_close\_time$.
2. **Trigger Condition Evaluation**:
   - `BID_RECEIVED`: True if bid is in trigger window.
   - `RANK_CHANGE`: True if the ranking vector of suppliers before this bid differs from the ranking vector after this bid.
   - `L1_CHANGE`: True if the supplier at rank $L1$ changes (either new carrier or old carrier ousted).
3. **Extension Application**:
   - Candidate new close time = $current\_bid\_close\_time + Y\text{ minutes}$.
   - Capped close time = $\min(candidate\_close\_time, forced\_bid\_close\_time)$.
   - If candidate exceeds forced close time: new close time becomes `forced_bid_close_time`, and log records capped extension.
   - If $current\_bid\_close\_time == forced\_bid\_close\_time$: no further extension is possible.
4. **State Transitions & Timers**:
   - If $current\_time < bid\_start\_time \implies$ `UPCOMING`
   - If $bid\_start\_time \le current\_time < current\_bid\_close\_time \implies$ `ACTIVE`
   - If $current\_time \ge current\_bid\_close\_time$:
     - If $current\_bid\_close\_time == forced\_bid\_close\_time \implies$ `FORCE_CLOSED`
     - Else $\implies$ `CLOSED`

### 2.5 Audit & Activity Logging
Every significant event must be stored in an immutable activity log table:
- `BID_SUBMITTED`: Carrier, total price, charges breakdown, resulting rank.
- `AUCTION_EXTENDED`: Previous close time, new close time, reason, trigger type, delta added.
- `EXTENSION_CAPPED`: When extension hits forced close limit.
- `AUCTION_CLOSED` / `AUCTION_FORCE_CLOSED`: Automated or scheduled closure.

---

## 3. Edge Cases & Boundary Conditions
1. **Simultaneous Bids**: Handled via serializable or row-level locking (`SELECT FOR UPDATE` on the RFQ record) so that rank calculation and extension time increments are atomic.
2. **Bid at exact close timestamp ($t = current\_bid\_close\_time$)**: Rejected as auction has closed.
3. **Trigger Window > Total Auction Duration**: Validation rule prevents $X \ge (bid\_close\_time - bid\_start\_time)$.
4. **Extension Duration pushing past Forced Close**: Capped safely at `forced_bid_close_time`.
5. **No Bids in Auction**: Closes at `bid_close_time` with no winner.
6. **Same carrier bidding again with higher price**: Rejected or ignored for ranking if not lower. In reverse auction, subsequent quotes from the same supplier must be lower than their previous lowest quote to qualify as competitive.
