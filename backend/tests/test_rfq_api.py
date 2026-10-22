from datetime import datetime, timedelta, timezone


def test_create_rfq_success(client):
    now = datetime.now(timezone.utc)
    payload = {
        "reference_id": "RFQ-TEST-001",
        "rfq_name": "Mumbai to Delhi 20FT Container",
        "bid_start_time": now.isoformat(),
        "bid_close_time": (now + timedelta(hours=2)).isoformat(),
        "forced_bid_close_time": (now + timedelta(hours=2, minutes=15)).isoformat(),
        "pickup_service_date": (now + timedelta(days=5)).isoformat(),
        "british_auction_enabled": True,
        "trigger_window_minutes": 10,
        "extension_duration_minutes": 5,
        "extension_trigger_type": "BID_RECEIVED",
    }
    response = client.post("/api/v1/rfqs", json=payload)
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["reference_id"] == "RFQ-TEST-001"
    assert data["status"] == "ACTIVE"
    assert data["extension_count"] == 0
    assert len(data["activity_logs"]) == 1
    assert data["activity_logs"][0]["event_type"] == "RFQ_CREATED"


def test_create_rfq_validation_forced_before_close(client):
    now = datetime.now(timezone.utc)
    payload = {
        "reference_id": "RFQ-TEST-INVALID-1",
        "rfq_name": "Invalid Timestamps",
        "bid_start_time": now.isoformat(),
        "bid_close_time": (now + timedelta(hours=2)).isoformat(),
        "forced_bid_close_time": (now + timedelta(hours=1)).isoformat(),  # Invalid: before close time
        "pickup_service_date": (now + timedelta(days=5)).isoformat(),
        "trigger_window_minutes": 10,
        "extension_duration_minutes": 5,
        "extension_trigger_type": "BID_RECEIVED",
    }
    response = client.post("/api/v1/rfqs", json=payload)
    assert response.status_code == 422  # Pydantic validation error


def test_create_rfq_duplicate_reference_rejected(client):
    now = datetime.now(timezone.utc)
    payload = {
        "reference_id": "RFQ-DUP-001",
        "rfq_name": "Test RFQ",
        "bid_start_time": now.isoformat(),
        "bid_close_time": (now + timedelta(hours=2)).isoformat(),
        "forced_bid_close_time": (now + timedelta(hours=2, minutes=15)).isoformat(),
        "pickup_service_date": (now + timedelta(days=5)).isoformat(),
        "trigger_window_minutes": 10,
        "extension_duration_minutes": 5,
        "extension_trigger_type": "BID_RECEIVED",
    }
    res1 = client.post("/api/v1/rfqs", json=payload)
    assert res1.status_code == 201

    res2 = client.post("/api/v1/rfqs", json=payload)
    assert res2.status_code == 409  # Conflict


def test_list_and_details_rfq(client):
    now = datetime.now(timezone.utc)
    payload = {
        "reference_id": "RFQ-LIST-001",
        "rfq_name": "Listable RFQ",
        "bid_start_time": now.isoformat(),
        "bid_close_time": (now + timedelta(hours=1)).isoformat(),
        "forced_bid_close_time": (now + timedelta(hours=1, minutes=20)).isoformat(),
        "pickup_service_date": (now + timedelta(days=2)).isoformat(),
        "trigger_window_minutes": 10,
        "extension_duration_minutes": 5,
        "extension_trigger_type": "BID_RECEIVED",
    }
    created = client.post("/api/v1/rfqs", json=payload).json()
    rfq_id = created["id"]

    # Test listing
    res_list = client.get("/api/v1/rfqs")
    assert res_list.status_code == 200
    summaries = res_list.json()
    assert any(s["id"] == rfq_id for s in summaries)

    # Test details
    res_detail = client.get(f"/api/v1/rfqs/{rfq_id}")
    assert res_detail.status_code == 200
    detail = res_detail.json()
    assert detail["reference_id"] == "RFQ-LIST-001"
    assert detail["rankings"] == []
