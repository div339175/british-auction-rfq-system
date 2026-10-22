import uuid
import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, update
from fastapi import HTTPException, status

from app.models.rfq import RFQ, AuctionStatus, ExtensionTriggerType
from app.models.quote import Quote
from app.models.activity_log import AuctionActivityLog, ActivityEventType
from app.schemas.quote import QuoteCreate, QuoteResponse
from app.engine.auction_engine import BritishAuctionEngine, CarrierBidEntry
from app.services.rfq_service import RFQService


class QuoteService:
    @staticmethod
    def _now_utc() -> datetime:
        return datetime.now(timezone.utc)

    @classmethod
    def submit_quote(
        cls,
        db: Session,
        rfq_id: str,
        data: QuoteCreate,
        submission_time: datetime | None = None,
    ) -> Tuple[Quote, Dict[str, Any]]:
        """
        Submits a supplier quote inside a serializable/pessimistic-locked transaction.
        Handles ranking changes, anti-sniping extensions, and audit trail.
        """
        now = submission_time or cls._now_utc()
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        # 1. Acquire row lock on RFQ to prevent concurrent race conditions
        # with_for_update() executes 'SELECT ... FOR UPDATE' in PostgreSQL
        query = select(RFQ).where(RFQ.id == rfq_id).with_for_update()
        rfq = db.execute(query).scalar_one_or_none()

        if not rfq:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"RFQ with ID '{rfq_id}' not found.",
            )

        # 2. Check and reconcile auction status
        rfq = RFQService.reconcile_rfq_status(rfq, db, now)

        if rfq.status in [AuctionStatus.CLOSED.value, AuctionStatus.FORCE_CLOSED.value]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot submit quote: Auction is {rfq.status}.",
            )

        # 3. Validate quote validity date against RFQ bid close time
        quote_validity = data.validity_date if data.validity_date.tzinfo else data.validity_date.replace(tzinfo=timezone.utc)
        rfq_close = rfq.bid_close_time if rfq.bid_close_time.tzinfo else rfq.bid_close_time.replace(tzinfo=timezone.utc)
        if quote_validity < rfq_close:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Quote validity date ({quote_validity.isoformat()}) must be on or after RFQ bid close time ({rfq_close.isoformat()}).",
            )

        # 4. Calculate total price
        total_price = Decimal(str(data.freight_charges)) + Decimal(str(data.origin_charges)) + Decimal(str(data.destination_charges))

        # 4. Fetch existing carrier quotes to build current state
        existing_quotes = (
            db.execute(
                select(Quote)
                .where(Quote.rfq_id == rfq_id)
                .order_by(Quote.submitted_at.asc())
            )
            .scalars()
            .all()
        )

        # Build map of best quote per carrier
        carrier_best_map: Dict[str, Quote] = {}
        for q in existing_quotes:
            c_name = q.carrier_name
            if c_name not in carrier_best_map or q.total_price < carrier_best_map[c_name].total_price:
                carrier_best_map[c_name] = q

        existing_entries = [
            CarrierBidEntry(
                carrier_name=q.carrier_name,
                best_price=q.total_price,
                submitted_at=q.submitted_at,
                quote_id=q.id,
            )
            for q in carrier_best_map.values()
        ]

        new_quote_id = str(uuid.uuid4())

        # 5. Evaluate through pure AuctionEngine
        eval_result = BritishAuctionEngine.evaluate_bid_submission(
            bid_time=now,
            bid_start_time=rfq.bid_start_time,
            current_close_time=rfq.bid_close_time,
            forced_close_time=rfq.forced_bid_close_time,
            british_auction_enabled=rfq.british_auction_enabled,
            trigger_window_minutes=rfq.trigger_window_minutes,
            extension_duration_minutes=rfq.extension_duration_minutes,
            trigger_type=ExtensionTriggerType(rfq.extension_trigger_type),
            existing_carrier_bids=existing_entries,
            new_carrier_name=data.carrier_name,
            new_total_price=total_price,
            new_quote_id=new_quote_id,
        )

        if not eval_result.is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=eval_result.error_message,
            )

        # Determine rank achieved by this carrier
        carrier_rank_item = next(
            (t for t in eval_result.new_ranking if t[0] == data.carrier_name),
            None,
        )
        rank_at_sub = carrier_rank_item[1] if carrier_rank_item else None

        # 6. Deprecate previous best flag for this carrier if any
        db.execute(
            update(Quote)
            .where(Quote.rfq_id == rfq_id, Quote.carrier_name == data.carrier_name)
            .values(is_carrier_best=False)
        )

        # 7. Insert the new Quote
        quote = Quote(
            id=new_quote_id,
            rfq_id=rfq_id,
            carrier_name=data.carrier_name,
            freight_charges=data.freight_charges,
            origin_charges=data.origin_charges,
            destination_charges=data.destination_charges,
            total_price=total_price,
            transit_time_days=data.transit_time_days,
            validity_date=data.validity_date,
            submitted_at=now,
            rank_at_submission=rank_at_sub,
            is_carrier_best=True,
        )
        db.add(quote)
        db.flush()

        # 8. If extension occurred, update RFQ and write extension activity log
        extension_info = {
            "extended": eval_result.should_extend,
            "previous_close_time": eval_result.previous_close_time.isoformat(),
            "new_close_time": eval_result.new_close_time.isoformat(),
            "is_capped": eval_result.is_capped,
            "reason": eval_result.extension_reason,
        }

        if eval_result.should_extend:
            rfq.bid_close_time = eval_result.new_close_time
            rfq.extension_count += 1
            rfq.updated_at = now

            ext_log = AuctionActivityLog(
                rfq_id=rfq_id,
                event_type=(
                    ActivityEventType.EXTENSION_CAPPED.value
                    if eval_result.is_capped
                    else ActivityEventType.AUCTION_EXTENDED.value
                ),
                carrier_name=data.carrier_name,
                quote_id=new_quote_id,
                previous_close_time=eval_result.previous_close_time,
                new_close_time=eval_result.new_close_time,
                message=eval_result.extension_reason,
                metadata_json=json.dumps({
                    "trigger_type": rfq.extension_trigger_type,
                    "extension_count": rfq.extension_count,
                    "is_capped": eval_result.is_capped,
                    "total_price": float(total_price),
                }),
            )
            db.add(ext_log)

        # 9. Record BID_SUBMITTED activity log
        bid_log = AuctionActivityLog(
            rfq_id=rfq_id,
            event_type=ActivityEventType.BID_SUBMITTED.value,
            carrier_name=data.carrier_name,
            quote_id=new_quote_id,
            message=(
                f"Quote submitted by {data.carrier_name}: Total ₹{total_price:,.2f} "
                f"(Freight: ₹{data.freight_charges:,.2f}, Origin: ₹{data.origin_charges:,.2f}, "
                f"Dest: ₹{data.destination_charges:,.2f}) - Ranked L{rank_at_sub or '?'}"
            ),
            metadata_json=json.dumps({
                "freight_charges": float(data.freight_charges),
                "origin_charges": float(data.origin_charges),
                "destination_charges": float(data.destination_charges),
                "total_price": float(total_price),
                "rank": f"L{rank_at_sub}" if rank_at_sub else None,
                "transit_time_days": data.transit_time_days,
            }),
        )
        db.add(bid_log)

        db.commit()
        db.refresh(quote)
        db.refresh(rfq)

        return quote, extension_info
