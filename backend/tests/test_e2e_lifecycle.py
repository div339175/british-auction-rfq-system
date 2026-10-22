from datetime import datetime, timedelta, timezone
from app.services.quote_service import QuoteService
from app.schemas.quote import QuoteCreate


def test_full_british_auction_journey(client, db_session):
    """
    End-to-End lifecycle test:
    1. Buyer creates RFQ with British Auction (Trigger X = 10m, Ext Y = 5m).
    2. Carrier Alpha places quote at 100,000 -> Becomes L1, triggers extension 1.
    3. Carrier Beta places quote at 95,000 -> Takes L1, triggers extension 2.
    4. Carrier Alpha re-bids at 92,000 at T0 -> Retakes L1, but close time is now T0+15m,
       so T0 is outside the new 10m trigger window [T0+5m, T0+15m). Valid bid, but no extension.
    5. Carrier Gamma submits bid at T0+7m (inside new trigger window) -> Triggers extension 3!
    6. Activity log records full immutable audit trail.
    """
    now = datetime.now(timezone.utc)
    rfq_payload = {
        "reference_id": f"E2E-{int(now.timestamp())}",
        "rfq_name": "Hamburg to Singapore Ocean Freight",
        "bid_start_time": (now - timedelta(minutes=15)).isoformat(),
        "bid_close_time": (now + timedelta(minutes=5)).isoformat(),  # Currently inside 10m trigger window
        "forced_bid_close_time": (now + timedelta(minutes=30)).isoformat(),
        "pickup_service_date": (now + timedelta(days=7)).isoformat(),
        "british_auction_enabled": True,
        "trigger_window_minutes": 10,
        "extension_duration_minutes": 5,
        "extension_trigger_type": "BID_RECEIVED",
    }
    rfq = client.post("/api/v1/rfqs", json=rfq_payload).json()
    rfq_id = rfq["id"]
    initial_close = datetime.fromisoformat(rfq["bid_close_time"])

    # Bid 1: Carrier Alpha (100k) at T0
    q1 = client.post(
        f"/api/v1/rfqs/{rfq_id}/quotes",
        json={
            "carrier_name": "Carrier Alpha",
            "freight_charges": 80000,
            "origin_charges": 10000,
            "destination_charges": 10000,
            "transit_time_days": 14,
            "validity_date": (now + timedelta(days=20)).isoformat(),
        },
    ).json()
    assert q1["quote"]["rank_at_submission"] == 1
    assert q1["extension_occurred"] is True

    # Bid 2: Carrier Beta (95k) at T0
    q2 = client.post(
        f"/api/v1/rfqs/{rfq_id}/quotes",
        json={
            "carrier_name": "Carrier Beta",
            "freight_charges": 75000,
            "origin_charges": 10000,
            "destination_charges": 10000,
            "transit_time_days": 12,
            "validity_date": (now + timedelta(days=20)).isoformat(),
        },
    ).json()
    assert q2["quote"]["rank_at_submission"] == 1
    assert q2["extension_occurred"] is True

    # Bid 3: Carrier Alpha underbids Beta at 92k at T0
    # Current close is now T0 + 15m.
    # The moving trigger window is [T0 + 5m, T0 + 15m).
    # Since T0 < T0 + 5m, this bid is outside the trigger window -> valid, ranks L1, no extension.
    q3 = client.post(
        f"/api/v1/rfqs/{rfq_id}/quotes",
        json={
            "carrier_name": "Carrier Alpha",
            "freight_charges": 72000,
            "origin_charges": 10000,
            "destination_charges": 10000,
            "transit_time_days": 13,
            "validity_date": (now + timedelta(days=20)).isoformat(),
        },
    ).json()
    assert q3["quote"]["rank_at_submission"] == 1
    assert q3["extension_occurred"] is False  # Correctly outside moving trigger window

    # Bid 4: Carrier Gamma submits at T0 + 7 minutes (inside [T0+5m, T0+15m) window)
    t_bid4 = now + timedelta(minutes=7)
    q4_in = QuoteCreate(
        carrier_name="Carrier Gamma",
        freight_charges=70000,
        origin_charges=10000,
        destination_charges=10000,
        transit_time_days=10,
        validity_date=now + timedelta(days=20),
    )
    quote4, ext4 = QuoteService.submit_quote(db_session, rfq_id, q4_in, submission_time=t_bid4)
    assert quote4.rank_at_submission == 1
    assert ext4["extended"] is True  # Triggers extension 3!

    # Verify Leaderboard
    details = client.get(f"/api/v1/rfqs/{rfq_id}").json()
    assert len(details["rankings"]) == 3
    assert details["rankings"][0]["carrier_name"] == "Carrier Gamma"
    assert details["rankings"][0]["rank_label"] == "L1"
    assert float(details["rankings"][0]["best_price"]) == 90000.0

    assert details["rankings"][1]["carrier_name"] == "Carrier Alpha"
    assert details["rankings"][1]["rank_label"] == "L2"
    assert float(details["rankings"][1]["best_price"]) == 92000.0

    assert details["rankings"][2]["carrier_name"] == "Carrier Beta"
    assert details["rankings"][2]["rank_label"] == "L3"
    assert float(details["rankings"][2]["best_price"]) == 95000.0

    # Total extensions must be 3 (from Bid 1, Bid 2, and Bid 4)
    assert details["extension_count"] == 3
    updated_close = datetime.fromisoformat(details["bid_close_time"])
    assert updated_close > initial_close

    # Verify Activity Logs
    logs = client.get(f"/api/v1/rfqs/{rfq_id}/logs").json()
    assert len(logs) >= 8  # 1 creation + 4 bids + 3 extensions
