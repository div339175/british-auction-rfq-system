from datetime import datetime, timedelta, timezone
from app.database import Base, engine, SessionLocal
from app.models.rfq import RFQ, AuctionStatus
from app.workers.tasks import reconcile_auction_statuses


def test_reconcile_auction_statuses_task():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    past_time = datetime.now(timezone.utc) - timedelta(minutes=5)
    # Create an expired RFQ
    rfq = RFQ(
        reference_id=f"EXPIRED-{datetime.now().timestamp()}",
        rfq_name="Expired Auction",
        status=AuctionStatus.ACTIVE.value,
        bid_start_time=past_time - timedelta(hours=1),
        bid_close_time=past_time,  # already passed
        original_bid_close_time=past_time,
        forced_bid_close_time=past_time + timedelta(minutes=10),
        pickup_service_date=datetime.now(timezone.utc) + timedelta(days=2),
        british_auction_enabled=True,
        trigger_window_minutes=10,
        extension_duration_minutes=5,
        extension_trigger_type="BID_RECEIVED",
        extension_count=0,
    )
    db.add(rfq)
    db.commit()
    rfq_id = rfq.id
    db.close()

    # Run the worker task synchronously
    reconciled = reconcile_auction_statuses()
    assert reconciled >= 1

    # Verify status changed to CLOSED
    db_verify = SessionLocal()
    updated = db_verify.query(RFQ).filter(RFQ.id == rfq_id).first()
    assert updated.status == AuctionStatus.CLOSED.value

    # Verify closure activity log was created
    from app.models.activity_log import AuctionActivityLog
    logs = db_verify.query(AuctionActivityLog).filter(AuctionActivityLog.rfq_id == rfq_id).all()
    assert any(l.event_type == "AUCTION_CLOSED" for l in logs)
    db_verify.close()
