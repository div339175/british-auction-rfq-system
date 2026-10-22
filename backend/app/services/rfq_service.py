import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_
from fastapi import HTTPException, status

from app.models.rfq import RFQ, AuctionStatus
from app.models.quote import Quote
from app.models.activity_log import AuctionActivityLog, ActivityEventType
from app.schemas.rfq import RFQCreate, RFQSummary, RFQDetailResponse
from app.schemas.quote import QuoteResponse, SupplierRankItem
from app.schemas.activity_log import ActivityLogResponse


class RFQService:
    @staticmethod
    def _now_utc() -> datetime:
        return datetime.now(timezone.utc)

    @classmethod
    def reconcile_rfq_status(cls, rfq: RFQ, db: Session, now: Optional[datetime] = None) -> RFQ:
        """
        Passive state reconciler. Ensures that if the clock has passed
        bid_start_time or bid_close_time, the RFQ state is accurately updated.
        """
        if now is None:
            now = cls._now_utc()

        # Ensure rfq timestamps are timezone aware for comparison
        def to_utc(dt: datetime) -> datetime:
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

        start = to_utc(rfq.bid_start_time)
        close = to_utc(rfq.bid_close_time)
        forced = to_utc(rfq.forced_bid_close_time)

        changed = False
        if rfq.status == AuctionStatus.UPCOMING.value and now >= start:
            rfq.status = AuctionStatus.ACTIVE.value
            changed = True
        elif rfq.status == AuctionStatus.ACTIVE.value and now >= close:
            if close >= forced or now >= forced:
                rfq.status = AuctionStatus.FORCE_CLOSED.value
                log_event = ActivityEventType.AUCTION_FORCE_CLOSED.value
                log_msg = f"Auction reached forced close deadline of {forced.strftime('%Y-%m-%d %H:%M:%S UTC')}."
            else:
                rfq.status = AuctionStatus.CLOSED.value
                log_event = ActivityEventType.AUCTION_CLOSED.value
                log_msg = f"Auction closed at scheduled close time {close.strftime('%Y-%m-%d %H:%M:%S UTC')}."

            # Log closure event
            closure_log = AuctionActivityLog(
                rfq_id=rfq.id,
                event_type=log_event,
                message=log_msg,
                previous_close_time=close,
                new_close_time=close,
            )
            db.add(closure_log)
            changed = True

        if changed:
            rfq.updated_at = now
            db.commit()
            db.refresh(rfq)

        return rfq

    @classmethod
    def create_rfq(cls, db: Session, data: RFQCreate) -> RFQ:
        # Check uniqueness of reference_id
        existing = db.execute(select(RFQ).where(RFQ.reference_id == data.reference_id)).scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"An RFQ with reference ID '{data.reference_id}' already exists.",
            )

        now = cls._now_utc()
        # Compute initial status
        start_utc = data.bid_start_time if data.bid_start_time.tzinfo else data.bid_start_time.replace(tzinfo=timezone.utc)
        close_utc = data.bid_close_time if data.bid_close_time.tzinfo else data.bid_close_time.replace(tzinfo=timezone.utc)

        if now < start_utc:
            initial_status = AuctionStatus.UPCOMING.value
        elif now >= close_utc:
            initial_status = AuctionStatus.CLOSED.value
        else:
            initial_status = AuctionStatus.ACTIVE.value

        rfq = RFQ(
            reference_id=data.reference_id,
            rfq_name=data.rfq_name,
            status=initial_status,
            bid_start_time=data.bid_start_time,
            bid_close_time=data.bid_close_time,
            original_bid_close_time=data.bid_close_time,
            forced_bid_close_time=data.forced_bid_close_time,
            pickup_service_date=data.pickup_service_date,
            british_auction_enabled=data.british_auction_enabled,
            trigger_window_minutes=data.trigger_window_minutes,
            extension_duration_minutes=data.extension_duration_minutes,
            extension_trigger_type=data.extension_trigger_type.value,
            extension_count=0,
        )
        db.add(rfq)
        db.flush()

        # Create initial activity log entry
        creation_log = AuctionActivityLog(
            rfq_id=rfq.id,
            event_type=ActivityEventType.RFQ_CREATED.value,
            message=f"RFQ '{rfq.rfq_name}' ({rfq.reference_id}) created with initial close time {rfq.bid_close_time.strftime('%Y-%m-%d %H:%M:%S')}.",
            metadata_json=json.dumps({
                "trigger_window_minutes": rfq.trigger_window_minutes,
                "extension_duration_minutes": rfq.extension_duration_minutes,
                "extension_trigger_type": rfq.extension_trigger_type,
            }),
        )
        db.add(creation_log)
        db.commit()
        db.refresh(rfq)
        return rfq

    @classmethod
    def list_rfqs(cls, db: Session, status_filter: Optional[str] = None) -> List[RFQSummary]:
        query = select(RFQ).order_by(RFQ.created_at.desc())
        rfqs = db.execute(query).scalars().all()

        summaries: List[RFQSummary] = []
        now = cls._now_utc()

        for rfq in rfqs:
            rfq = cls.reconcile_rfq_status(rfq, db, now)
            if status_filter and rfq.status != status_filter:
                continue

            # Query lowest bid for this RFQ
            lowest_quote = (
                db.execute(
                    select(Quote)
                    .where(Quote.rfq_id == rfq.id)
                    .order_by(Quote.total_price.asc(), Quote.submitted_at.asc())
                )
                .scalars()
                .first()
            )

            summaries.append(
                RFQSummary(
                    id=rfq.id,
                    reference_id=rfq.reference_id,
                    rfq_name=rfq.rfq_name,
                    status=AuctionStatus(rfq.status),
                    bid_start_time=rfq.bid_start_time,
                    bid_close_time=rfq.bid_close_time,
                    forced_bid_close_time=rfq.forced_bid_close_time,
                    current_lowest_bid=lowest_quote.total_price if lowest_quote else None,
                    current_lowest_carrier=lowest_quote.carrier_name if lowest_quote else None,
                    extension_count=rfq.extension_count,
                    british_auction_enabled=rfq.british_auction_enabled,
                    trigger_window_minutes=rfq.trigger_window_minutes,
                    extension_duration_minutes=rfq.extension_duration_minutes,
                    extension_trigger_type=rfq.extension_trigger_type,
                )
            )

        return summaries

    @classmethod
    def get_rfq_details(cls, db: Session, rfq_id: str) -> RFQDetailResponse:
        rfq = db.execute(select(RFQ).where(RFQ.id == rfq_id)).scalar_one_or_none()
        if not rfq:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"RFQ with ID '{rfq_id}' not found.",
            )

        rfq = cls.reconcile_rfq_status(rfq, db)

        # 1. Fetch all quotes sorted newest first
        all_quotes = (
            db.execute(
                select(Quote)
                .where(Quote.rfq_id == rfq.id)
                .order_by(Quote.submitted_at.desc())
            )
            .scalars()
            .all()
        )

        # 2. Compute supplier ranking leaderboard
        # Find best (lowest total_price) quote per carrier
        carrier_best: dict[str, Quote] = {}
        # Iterate in chronological order to resolve ties with earlier submitted_at
        for q in reversed(all_quotes):
            c_name = q.carrier_name
            if c_name not in carrier_best or q.total_price < carrier_best[c_name].total_price:
                carrier_best[c_name] = q

        sorted_best_quotes = sorted(carrier_best.values(), key=lambda q: (q.total_price, q.submitted_at))

        rankings: List[SupplierRankItem] = []
        for idx, q in enumerate(sorted_best_quotes):
            rank_num = idx + 1
            rankings.append(
                SupplierRankItem(
                    carrier_name=q.carrier_name,
                    rank_label=f"L{rank_num}",
                    rank_number=rank_num,
                    best_price=q.total_price,
                    quote_id=q.id,
                    submitted_at=q.submitted_at,
                    transit_time_days=q.transit_time_days,
                    validity_date=q.validity_date,
                )
            )

        lowest_quote = sorted_best_quotes[0] if sorted_best_quotes else None

        # 3. Fetch activity logs
        logs = (
            db.execute(
                select(AuctionActivityLog)
                .where(AuctionActivityLog.rfq_id == rfq.id)
                .order_by(AuctionActivityLog.created_at.desc())
            )
            .scalars()
            .all()
        )

        return RFQDetailResponse(
            id=rfq.id,
            reference_id=rfq.reference_id,
            rfq_name=rfq.rfq_name,
            status=AuctionStatus(rfq.status),
            bid_start_time=rfq.bid_start_time,
            bid_close_time=rfq.bid_close_time,
            original_bid_close_time=rfq.original_bid_close_time,
            forced_bid_close_time=rfq.forced_bid_close_time,
            pickup_service_date=rfq.pickup_service_date,
            british_auction_enabled=rfq.british_auction_enabled,
            trigger_window_minutes=rfq.trigger_window_minutes,
            extension_duration_minutes=rfq.extension_duration_minutes,
            extension_trigger_type=rfq.extension_trigger_type,
            extension_count=rfq.extension_count,
            current_lowest_bid=lowest_quote.total_price if lowest_quote else None,
            current_lowest_carrier=lowest_quote.carrier_name if lowest_quote else None,
            created_at=rfq.created_at,
            updated_at=rfq.updated_at,
            rankings=rankings,
            quotes=[QuoteResponse.model_validate(q) for q in all_quotes],
            activity_logs=[ActivityLogResponse.model_validate(l) for l in logs],
        )
