from datetime import datetime, timedelta, timezone
from decimal import Decimal


def create_sample_rfq(client, close_minutes=60, forced_minutes=75, trigger_window=10, ext_duration=5, trigger_type="BID_RECEIVED"):
    now = datetime.now(timezone.utc)
    payload = {
        "reference_id": f"RFQ-{datetime.now().timestamp()}",
        "rfq_name": "Freight Test Shipment",
        "bid_start_time": (now - timedelta(minutes=10)).isoformat(),
        "bid_close_time": (now + timedelta(minutes=close_minutes)).isoformat(),
        "forced_bid_close_time": (now + timedelta(minutes=forced_minutes)).isoformat(),
        "pickup_service_date": (now + timedelta(days=3)).isoformat(),
        "british_auction_enabled": True,
        "trigger_window_minutes": trigger_window,
        "extension_duration_minutes": ext_duration,
        "extension_trigger_type": trigger_type,
    }
    res = client.post("/api/v1/rfqs", json=payload)
    assert res.status_code == 201
    return res.json()


def test_quote_submission_and_ranking(client):
    rfq = create_sample_rfq(client)
    rfq_id = rfq["id"]

    # Carrier Alpha submits quote: 50k + 10k + 10k = 70k
    quote1_payload = {
        "carrier_name": "Carrier Alpha",
        "freight_charges": 50000.0,
        "origin_charges": 10000.0,
        "destination_charges": 10000.0,
        "transit_time_days": 4,
        "validity_date": (datetime.now(timezone.utc) + timedelta(days=10)).isoformat(),
    }
    res1 = client.post(f"/api/v1/rfqs/{rfq_id}/quotes", json=quote1_payload)
    assert res1.status_code == 201
    data1 = res1.json()
    assert float(data1["quote"]["total_price"]) == 70000.0
    assert data1["quote"]["rank_at_submission"] == 1

    # Carrier Beta submits lower quote: 45k + 10k + 10k = 65k -> Becomes L1
    quote2_payload = {
        "carrier_name": "Carrier Beta",
        "freight_charges": 45000.0,
        "origin_charges": 10000.0,
        "destination_charges": 10000.0,
        "transit_time_days": 3,
        "validity_date": (datetime.now(timezone.utc) + timedelta(days=10)).isoformat(),
    }
    res2 = client.post(f"/api/v1/rfqs/{rfq_id}/quotes", json=quote2_payload)
    assert res2.status_code == 201
    data2 = res2.json()
    assert float(data2["quote"]["total_price"]) == 65000.0
    assert data2["quote"]["rank_at_submission"] == 1

    # Verify RFQ details shows rankings: L1 = Beta (65k), L2 = Alpha (70k)
    details = client.get(f"/api/v1/rfqs/{rfq_id}").json()
    assert len(details["rankings"]) == 2
    assert details["rankings"][0]["carrier_name"] == "Carrier Beta"
    assert details["rankings"][0]["rank_label"] == "L1"
    assert float(details["rankings"][0]["best_price"]) == 65000.0

    assert details["rankings"][1]["carrier_name"] == "Carrier Alpha"
    assert details["rankings"][1]["rank_label"] == "L2"
    assert float(details["rankings"][1]["best_price"]) == 70000.0


def test_quote_extension_in_trigger_window(client, monkeypatch):
    """
    Simulate RFQ with close time 5 minutes from now.
    Trigger window = 10 minutes.
    Submitting a quote must extend the auction by 5 minutes.
    """
    now = datetime.now(timezone.utc)
    rfq = create_sample_rfq(client, close_minutes=5, forced_minutes=25, trigger_window=10, ext_duration=5)
    rfq_id = rfq["id"]

    initial_close = datetime.fromisoformat(rfq["bid_close_time"])

    quote_payload = {
        "carrier_name": "Carrier Swift",
        "freight_charges": 60000.0,
        "origin_charges": 5000.0,
        "destination_charges": 5000.0,
        "transit_time_days": 2,
        "validity_date": (now + timedelta(days=10)).isoformat(),
    }
    res = client.post(f"/api/v1/rfqs/{rfq_id}/quotes", json=quote_payload)
    assert res.status_code == 201
    data = res.json()
    assert data["extension_occurred"] is True

    # Verify details reflect extended close time and incremented extension count
    details = client.get(f"/api/v1/rfqs/{rfq_id}").json()
    new_close = datetime.fromisoformat(details["bid_close_time"])
    assert details["extension_count"] == 1
    assert (new_close - initial_close).total_seconds() == 5 * 60

    # Verify activity logs contain both BID_SUBMITTED and AUCTION_EXTENDED
    logs = client.get(f"/api/v1/rfqs/{rfq_id}/logs").json()
    event_types = [l["event_type"] for l in logs]
    assert "BID_SUBMITTED" in event_types
    assert "AUCTION_EXTENDED" in event_types


def test_quote_validity_validation(client):
    """
    Test business rule: validity_date >= rfq.bid_close_time
    1. validity_date before bid_close_time -> rejected (400)
    2. validity_date exactly equal to bid_close_time -> accepted (201)
    3. validity_date after bid_close_time -> accepted (201)
    """
    now = datetime.now(timezone.utc)
    rfq = create_sample_rfq(client, close_minutes=30, forced_minutes=45)
    rfq_id = rfq["id"]
    close_time = datetime.fromisoformat(rfq["bid_close_time"])

    # 1. Validity date before bid_close_time -> Rejected
    payload_before = {
        "carrier_name": "Carrier EarlyExpire",
        "freight_charges": 50000.0,
        "origin_charges": 5000.0,
        "destination_charges": 5000.0,
        "transit_time_days": 3,
        "validity_date": (close_time - timedelta(minutes=5)).isoformat(),
    }
    res_before = client.post(f"/api/v1/rfqs/{rfq_id}/quotes", json=payload_before)
    assert res_before.status_code == 400
    assert "must be on or after RFQ bid close time" in res_before.json()["detail"]

    # 2. Validity date exactly equal to bid_close_time -> Accepted
    payload_equal = {
        "carrier_name": "Carrier ExactExpire",
        "freight_charges": 48000.0,
        "origin_charges": 5000.0,
        "destination_charges": 5000.0,
        "transit_time_days": 3,
        "validity_date": close_time.isoformat(),
    }
    res_equal = client.post(f"/api/v1/rfqs/{rfq_id}/quotes", json=payload_equal)
    assert res_equal.status_code == 201

    # 3. Validity date after bid_close_time -> Accepted
    payload_after = {
        "carrier_name": "Carrier LaterExpire",
        "freight_charges": 46000.0,
        "origin_charges": 5000.0,
        "destination_charges": 5000.0,
        "transit_time_days": 3,
        "validity_date": (close_time + timedelta(hours=2)).isoformat(),
    }
    res_after = client.post(f"/api/v1/rfqs/{rfq_id}/quotes", json=payload_after)
    assert res_after.status_code == 201
