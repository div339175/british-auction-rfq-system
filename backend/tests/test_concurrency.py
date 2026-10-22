import threading
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy.orm import Session
from app.database import Base, engine, SessionLocal
from app.models.rfq import RFQ, ExtensionTriggerType
from app.schemas.quote import QuoteCreate
from app.services.quote_service import QuoteService


def test_concurrent_bids_serialized():
    """
    Test concurrent bid submission by multiple threads.
    Simulates Supplier A (95k), Supplier B (94k), and Supplier C (93k)
    submitting almost simultaneously in the trigger window.
    Verifies that all bids are ingested with correct rankings and consistent extension state.
    """
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    now = datetime.now(timezone.utc)
    # RFQ close is in 5 minutes, trigger window is 10m -> bids will trigger extension
    rfq = RFQ(
        reference_id=f"CONCURRENCY-TEST-{datetime.now().timestamp()}",
        rfq_name="Concurrent Shipment Bidding",
        status="ACTIVE",
        bid_start_time=now - timedelta(minutes=10),
        bid_close_time=now + timedelta(minutes=5),
        original_bid_close_time=now + timedelta(minutes=5),
        forced_bid_close_time=now + timedelta(minutes=30),
        pickup_service_date=now + timedelta(days=2),
        british_auction_enabled=True,
        trigger_window_minutes=10,
        extension_duration_minutes=5,
        extension_trigger_type=ExtensionTriggerType.BID_RECEIVED.value,
        extension_count=0,
    )
    db.add(rfq)
    db.commit()
    db.refresh(rfq)
    rfq_id = rfq.id
    db.close()

    carriers_data = [
        ("Supplier A", Decimal("80000.00"), Decimal("7500.00"), Decimal("7500.00")),  # Total 95,000
        ("Supplier B", Decimal("79000.00"), Decimal("7500.00"), Decimal("7500.00")),  # Total 94,000
        ("Supplier C", Decimal("78000.00"), Decimal("7500.00"), Decimal("7500.00")),  # Total 93,000
        ("Supplier D", Decimal("77000.00"), Decimal("7500.00"), Decimal("7500.00")),  # Total 92,000
    ]

    results = []
    errors = []

    def submit_worker(carrier_name, f, o, d):
        thread_db = SessionLocal()
        try:
            quote_in = QuoteCreate(
                carrier_name=carrier_name,
                freight_charges=f,
                origin_charges=o,
                destination_charges=d,
                transit_time_days=3,
                validity_date=now + timedelta(days=5),
            )
            quote, ext_info = QuoteService.submit_quote(thread_db, rfq_id, quote_in)
            results.append((carrier_name, quote.total_price, ext_info))
        except Exception as e:
            errors.append((carrier_name, str(e)))
        finally:
            thread_db.close()

    # Launch threads concurrently
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(submit_worker, c[0], c[1], c[2], c[3])
            for c in carriers_data
        ]
        for f in futures:
            f.result()

    assert len(errors) == 0, f"Concurrent submission encountered errors: {errors}"
    assert len(results) == 4

    # Verify final state in database
    verify_db = SessionLocal()
    updated_rfq = verify_db.query(RFQ).filter(RFQ.id == rfq_id).first()

    # Each bid triggered an extension because each arrived in the moving trigger window
    assert updated_rfq.extension_count >= 1
    assert updated_rfq.bid_close_time <= updated_rfq.forced_bid_close_time

    # Verify quotes count
    from app.models.quote import Quote
    quotes = verify_db.query(Quote).filter(Quote.rfq_id == rfq_id).all()
    assert len(quotes) == 4

    # Verify lowest price is Supplier D with 92,000
    lowest_quote = min(quotes, key=lambda q: q.total_price)
    assert lowest_quote.carrier_name == "Supplier D"
    assert lowest_quote.total_price == Decimal("92000.00")

    verify_db.close()
