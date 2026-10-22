from datetime import datetime, timezone
from sqlalchemy import select
from app.workers.celery_app import celery_app
from app.database import SessionLocal
from app.models.rfq import RFQ, AuctionStatus
from app.services.rfq_service import RFQService


@celery_app.task(name="app.workers.tasks.reconcile_auction_statuses")
def reconcile_auction_statuses() -> int:
    """
    Periodic background job triggered by Celery Beat every 5 seconds.
    Scans for open (UPCOMING / ACTIVE) RFQs and reconciles their status
    if the clock has passed their scheduled close time or forced close time.
    """
    db = SessionLocal()
    reconciled_count = 0
    now = datetime.now(timezone.utc)
    try:
        active_rfqs = (
            db.execute(
                select(RFQ).where(
                    RFQ.status.in_([AuctionStatus.UPCOMING.value, AuctionStatus.ACTIVE.value])
                )
            )
            .scalars()
            .all()
        )

        for rfq in active_rfqs:
            prev_status = rfq.status
            RFQService.reconcile_rfq_status(rfq, db, now)
            if rfq.status != prev_status:
                reconciled_count += 1

        return reconciled_count
    finally:
        db.close()


@celery_app.task(name="app.workers.tasks.close_single_auction")
def close_single_auction(rfq_id: str) -> bool:
    """Explicitly closes a specific auction if its deadline has arrived."""
    db = SessionLocal()
    try:
        rfq = db.execute(select(RFQ).where(RFQ.id == rfq_id)).scalar_one_or_none()
        if not rfq:
            return False
        RFQService.reconcile_rfq_status(rfq, db)
        return True
    finally:
        db.close()
