from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.rfq import RFQCreate, RFQSummary, RFQDetailResponse
from app.services.rfq_service import RFQService

router = APIRouter(prefix="/rfqs", tags=["RFQs"])


@router.post("", response_model=RFQDetailResponse, status_code=status.HTTP_201_CREATED)
def create_rfq(data: RFQCreate, db: Session = Depends(get_db)):
    """Create a new RFQ configured with British Auction rules."""
    rfq = RFQService.create_rfq(db, data)
    return RFQService.get_rfq_details(db, rfq.id)


@router.get("", response_model=List[RFQSummary])
def list_rfqs(
    status: Optional[str] = Query(None, description="Filter by status: UPCOMING, ACTIVE, CLOSED, FORCE_CLOSED"),
    db: Session = Depends(get_db),
):
    """List all RFQs with current summary status and lowest bid for the listing page."""
    return RFQService.list_rfqs(db, status_filter=status)


@router.get("/{rfq_id}", response_model=RFQDetailResponse)
def get_rfq_details(rfq_id: str, db: Session = Depends(get_db)):
    """Get full details of a specific RFQ, including supplier rankings, quote history, and activity logs."""
    return RFQService.get_rfq_details(db, rfq_id)
