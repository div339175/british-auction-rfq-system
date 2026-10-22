from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional, Tuple
from app.models.rfq import ExtensionTriggerType


@dataclass(frozen=True)
class CarrierBidEntry:
    carrier_name: str
    best_price: Decimal
    submitted_at: datetime
    quote_id: str


@dataclass
class EngineEvaluationResult:
    is_valid: bool
    error_message: Optional[str]
    rank_changed: bool
    l1_changed: bool
    previous_l1: Optional[str]
    new_l1: Optional[str]
    is_in_trigger_window: bool
    should_extend: bool
    previous_close_time: datetime
    new_close_time: datetime
    is_capped: bool
    extension_reason: Optional[str]
    new_ranking: List[Tuple[str, int, Decimal]]  # List of (carrier_name, rank_number, best_price)


class BritishAuctionEngine:
    """
    Pure domain auction engine.
    Encapsulates all anti-sniping, ranking, trigger window, and forced close clamping logic.
    Zero database or network dependencies for absolute testability.
    """

    @staticmethod
    def evaluate_bid_submission(
        *,
        bid_time: datetime,
        bid_start_time: datetime,
        current_close_time: datetime,
        forced_close_time: datetime,
        british_auction_enabled: bool,
        trigger_window_minutes: int,
        extension_duration_minutes: int,
        trigger_type: ExtensionTriggerType,
        existing_carrier_bids: List[CarrierBidEntry],
        new_carrier_name: str,
        new_total_price: Decimal,
        new_quote_id: str,
    ) -> EngineEvaluationResult:
        # Standardize timezones: ensure all datetimes are UTC aware for consistent math
        def to_utc(dt: datetime) -> datetime:
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)

        b_time = to_utc(bid_time)
        s_time = to_utc(bid_start_time)
        c_time = to_utc(current_close_time)
        f_time = to_utc(forced_close_time)

        # 1. Auction Timeline Validation
        if b_time < s_time:
            return EngineEvaluationResult(
                is_valid=False,
                error_message=f"Bid submitted at {b_time.isoformat()} before auction start time {s_time.isoformat()}.",
                rank_changed=False,
                l1_changed=False,
                previous_l1=None,
                new_l1=None,
                is_in_trigger_window=False,
                should_extend=False,
                previous_close_time=c_time,
                new_close_time=c_time,
                is_capped=False,
                extension_reason=None,
                new_ranking=[],
            )

        if b_time >= c_time:
            return EngineEvaluationResult(
                is_valid=False,
                error_message=f"Auction closed at {c_time.isoformat()}. Bid submitted at {b_time.isoformat()} was rejected.",
                rank_changed=False,
                l1_changed=False,
                previous_l1=None,
                new_l1=None,
                is_in_trigger_window=False,
                should_extend=False,
                previous_close_time=c_time,
                new_close_time=c_time,
                is_capped=False,
                extension_reason=None,
                new_ranking=[],
            )

        if b_time >= f_time:
            return EngineEvaluationResult(
                is_valid=False,
                error_message=f"Auction forced close deadline was {f_time.isoformat()}. Bid submitted at {b_time.isoformat()} was rejected.",
                rank_changed=False,
                l1_changed=False,
                previous_l1=None,
                new_l1=None,
                is_in_trigger_window=False,
                should_extend=False,
                previous_close_time=c_time,
                new_close_time=c_time,
                is_capped=False,
                extension_reason=None,
                new_ranking=[],
            )

        # 2. Competitive Price Validation
        # In a reverse auction, a supplier must bid strictly lower than their own prior best bid.
        existing_for_carrier = next((cb for cb in existing_carrier_bids if cb.carrier_name == new_carrier_name), None)
        if existing_for_carrier and new_total_price >= existing_for_carrier.best_price:
            return EngineEvaluationResult(
                is_valid=False,
                error_message=(
                    f"Submitted quote of {new_total_price} is not lower than carrier's existing best quote "
                    f"of {existing_for_carrier.best_price}."
                ),
                rank_changed=False,
                l1_changed=False,
                previous_l1=None,
                new_l1=None,
                is_in_trigger_window=False,
                should_extend=False,
                previous_close_time=c_time,
                new_close_time=c_time,
                is_capped=False,
                extension_reason=None,
                new_ranking=[],
            )

        # 3. Compute Rankings (Before vs After)
        # Sort key: (best_price ASC, submitted_at ASC)
        sorted_before = sorted(existing_carrier_bids, key=lambda x: (x.best_price, to_utc(x.submitted_at)))
        previous_ranking_order = [cb.carrier_name for cb in sorted_before]
        previous_l1 = sorted_before[0].carrier_name if sorted_before else None

        # Build new list of carrier entries
        new_entries: List[CarrierBidEntry] = []
        carrier_seen = False
        for cb in existing_carrier_bids:
            if cb.carrier_name == new_carrier_name:
                carrier_seen = True
                new_entries.append(
                    CarrierBidEntry(
                        carrier_name=new_carrier_name,
                        best_price=new_total_price,
                        submitted_at=b_time,
                        quote_id=new_quote_id,
                    )
                )
            else:
                new_entries.append(cb)

        if not carrier_seen:
            new_entries.append(
                CarrierBidEntry(
                    carrier_name=new_carrier_name,
                    best_price=new_total_price,
                    submitted_at=b_time,
                    quote_id=new_quote_id,
                )
            )

        sorted_after = sorted(new_entries, key=lambda x: (x.best_price, to_utc(x.submitted_at)))
        new_ranking_order = [cb.carrier_name for cb in sorted_after]
        new_l1 = sorted_after[0].carrier_name if sorted_after else None

        rank_changed = previous_ranking_order != new_ranking_order
        l1_changed = previous_l1 != new_l1

        new_ranking_tuples: List[Tuple[str, int, Decimal]] = [
            (entry.carrier_name, rank_idx + 1, entry.best_price)
            for rank_idx, entry in enumerate(sorted_after)
        ]

        # 4. Trigger Window & Extension Evaluation
        trigger_window_start = c_time - timedelta(minutes=trigger_window_minutes)
        is_in_trigger_window = trigger_window_start <= b_time < c_time

        should_extend = False
        extension_reason = None
        new_close = c_time
        is_capped = False

        if british_auction_enabled and is_in_trigger_window:
            # Check trigger type condition
            if trigger_type == ExtensionTriggerType.BID_RECEIVED:
                should_extend = True
                extension_reason = (
                    f"Bid received from {new_carrier_name} at {b_time.strftime('%H:%M:%S')} "
                    f"within {trigger_window_minutes}m trigger window ({trigger_window_start.strftime('%H:%M:%S')} - {c_time.strftime('%H:%M:%S')})."
                )
            elif trigger_type == ExtensionTriggerType.RANK_CHANGE:
                if rank_changed:
                    should_extend = True
                    extension_reason = (
                        f"Supplier rank change triggered by {new_carrier_name} ({new_total_price}) "
                        f"within {trigger_window_minutes}m trigger window."
                    )
            elif trigger_type == ExtensionTriggerType.L1_CHANGE:
                if l1_changed:
                    should_extend = True
                    extension_reason = (
                        f"Lowest bidder (L1) changed from {previous_l1 or 'None'} to {new_l1} ({new_total_price}) "
                        f"within {trigger_window_minutes}m trigger window."
                    )

        # 5. Extension Calculation & Forced Close Clamping
        if should_extend:
            if c_time >= f_time:
                # Already at forced close ceiling
                should_extend = False
                new_close = f_time
                is_capped = True
                extension_reason = (
                    f"Extension skipped: Auction has already reached forced close deadline ({f_time.strftime('%H:%M:%S')})."
                )
            else:
                candidate_close = c_time + timedelta(minutes=extension_duration_minutes)
                if candidate_close > f_time:
                    new_close = f_time
                    is_capped = True
                    extension_reason = (
                        f"{extension_reason} Extension clamped to forced close deadline ({f_time.strftime('%H:%M:%S')})."
                    )
                else:
                    new_close = candidate_close
                    is_capped = False
                    extension_reason = (
                        f"{extension_reason} Auction extended by {extension_duration_minutes}m from "
                        f"{c_time.strftime('%H:%M:%S')} to {new_close.strftime('%H:%M:%S')}."
                    )

        return EngineEvaluationResult(
            is_valid=True,
            error_message=None,
            rank_changed=rank_changed,
            l1_changed=l1_changed,
            previous_l1=previous_l1,
            new_l1=new_l1,
            is_in_trigger_window=is_in_trigger_window,
            should_extend=should_extend,
            previous_close_time=c_time,
            new_close_time=new_close,
            is_capped=is_capped,
            extension_reason=extension_reason,
            new_ranking=new_ranking_tuples,
        )
