from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.database import get_db
from app.models.activity_log import AuctionActivityLog
from app.schemas.activity_log import ActivityLogResponse

router = APIRouter(prefix="/rfqs/{rfq_id}/logs", tags=["Activity Logs"])


@router.get("", response_model=List[ActivityLogResponse])
def get_rfq_activity_logs(rfq_id: str, db: Session = Depends(get_db)):
    """Fetch complete chronological activity log for an RFQ."""
    logs = (
        db.execute(
            select(AuctionActivityLog)
            .where(AuctionActivityLog.rfq_id == rfq_id)
            .order_by(AuctionActivityLog.created_at.desc())
        )
        .scalars()
        .all()
    )
    return [ActivityLogResponse.model_validate(log) for log in logs]
