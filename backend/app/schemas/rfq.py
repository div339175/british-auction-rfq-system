from datetime import datetime
from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel, Field, model_validator
from app.models.rfq import AuctionStatus, ExtensionTriggerType
from app.schemas.quote import QuoteResponse, SupplierRankItem
from app.schemas.activity_log import ActivityLogResponse


class RFQCreate(BaseModel):
    reference_id: str = Field(..., min_length=2, max_length=64, description="Unique RFQ reference ID (e.g. RFQ-2026-001)")
    rfq_name: str = Field(..., min_length=2, max_length=255, description="Descriptive name of the RFQ")
    bid_start_time: datetime = Field(..., description="Start of bidding")
    bid_close_time: datetime = Field(..., description="Initial close time")
    forced_bid_close_time: datetime = Field(..., description="Absolute forced close time (must be > bid_close_time)")
    pickup_service_date: datetime = Field(..., description="Required pickup or service date")

    british_auction_enabled: bool = Field(True, description="Enable British Auction dynamic extension logic")
    trigger_window_minutes: int = Field(10, gt=0, description="Trigger window (X minutes)")
    extension_duration_minutes: int = Field(5, gt=0, description="Extension duration (Y minutes)")
    extension_trigger_type: ExtensionTriggerType = Field(
        ExtensionTriggerType.BID_RECEIVED,
        description="Trigger condition: BID_RECEIVED, RANK_CHANGE, or L1_CHANGE",
    )

    @model_validator(mode="after")
    def validate_timestamps(self):
        if self.bid_close_time <= self.bid_start_time:
            raise ValueError("Bid Close Time must be strictly later than Bid Start Time.")
        if self.forced_bid_close_time <= self.bid_close_time:
            raise ValueError("Forced Bid Close Time must be strictly later than Bid Close Time.")
        total_duration_minutes = (self.bid_close_time - self.bid_start_time).total_seconds() / 60
        if self.trigger_window_minutes > total_duration_minutes:
            raise ValueError(
                f"Trigger window ({self.trigger_window_minutes}m) cannot exceed total auction duration ({total_duration_minutes:.1f}m)."
            )
        return self


class RFQSummary(BaseModel):
    id: str
    reference_id: str
    rfq_name: str
    status: AuctionStatus
    bid_start_time: datetime
    bid_close_time: datetime
    forced_bid_close_time: datetime
    current_lowest_bid: Optional[Decimal] = None
    current_lowest_carrier: Optional[str] = None
    extension_count: int
    british_auction_enabled: bool
    trigger_window_minutes: int
    extension_duration_minutes: int
    extension_trigger_type: ExtensionTriggerType

    model_config = {"from_attributes": True}


class RFQDetailResponse(BaseModel):
    id: str
    reference_id: str
    rfq_name: str
    status: AuctionStatus
    bid_start_time: datetime
    bid_close_time: datetime
    original_bid_close_time: datetime
    forced_bid_close_time: datetime
    pickup_service_date: datetime
    british_auction_enabled: bool
    trigger_window_minutes: int
    extension_duration_minutes: int
    extension_trigger_type: ExtensionTriggerType
    extension_count: int
    current_lowest_bid: Optional[Decimal] = None
    current_lowest_carrier: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    # Leaderboard of carriers (sorted by rank: L1, L2, L3...)
    rankings: List[SupplierRankItem] = []

    # All submitted quotes (sorted newest first)
    quotes: List[QuoteResponse] = []

    # Chronological activity logs (newest first)
    activity_logs: List[ActivityLogResponse] = []

    model_config = {"from_attributes": True}
