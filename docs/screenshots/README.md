# Application Screenshots Guide

This directory is designated for visual walkthrough captures of the British Auction RFQ System.

### Key UI Views:
1. **Auction Listing Page** (`01_auction_listing.png`):
   - Overview of all British Auctions with status badges (`ACTIVE`, `CLOSED`, `FORCE_CLOSED`, `UPCOMING`).
   - Displays Current Lowest Bid ($L1$), dynamic close time, forced close time, and extension counter.
   - Filter tabs for fast navigation across auction states.

2. **Create RFQ Modal** (`02_create_rfq_modal.png`):
   - Input fields for RFQ Title, Reference ID, Bid Start, Bid Close, Forced Bid Close, and Service Date.
   - British Auction anti-sniping configuration: Trigger Window ($X$ minutes), Extension Duration ($Y$ minutes), and Trigger Condition dropdown.

3. **Auction Details & Live Clock** (`03_auction_details.png`):
   - Authoritative countdown clock synced with backend close time.
   - Anti-sniping warning banner when bidding activity is within the $X$-minute trigger window.
   - Hard Cap Forced Close indicator.

4. **Dynamic Supplier Leaderboard & Quote History** (`04_leaderboard_and_quotes.png`):
   - Leaderboard showing active competitors ranked $L1, L2, L3, \dots$ sorted by price.
   - Interactive quote submission form with live calculated sum of freight, origin, and destination charges.
   - Submitted Quote History table with user-controlled sorting toggle (`Lowest Price First` vs `Newest First`).

5. **Chronological Activity Log & Audit Trail** (`05_activity_log.png`):
   - Real-time audit log recording quote placements, time extensions, explicit extension reasons, and state transitions.

6. **Swagger / OpenAPI Documentation** (`06_swagger_api_docs.png`):
   - Interactive API documentation available at `http://localhost:8000/docs`.
