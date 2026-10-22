from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.quote import QuoteCreate, QuoteResponse
from app.services.quote_service import QuoteService

router = APIRouter(tags=["Quotes"])


class QuoteSubmissionResponse(BaseModel):
    quote: QuoteResponse
    extension_occurred: bool
    new_close_time: str
    message: str


@router.post("/rfqs/{rfq_id}/quotes", response_model=QuoteSubmissionResponse, status_code=status.HTTP_201_CREATED)
def submit_quote(
    rfq_id: str,
    data: QuoteCreate,
    db: Session = Depends(get_db),
):
    """
    Submit a quote for an RFQ.
    Atomically evaluates ranking, trigger window, anti-sniping extension, and forced close cap.
    """
    quote, ext_info = QuoteService.submit_quote(db, rfq_id, data)
    return QuoteSubmissionResponse(
        quote=QuoteResponse.model_validate(quote),
        extension_occurred=ext_info["extended"],
        new_close_time=ext_info["new_close_time"],
        message=ext_info["reason"] or f"Quote placed successfully (Rank: L{quote.rank_at_submission or '?'})",
    )
