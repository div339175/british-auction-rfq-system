import uuid
from datetime import datetime, timezone
from enum import Enum
from sqlalchemy import (
    Column,
    String,
    Boolean,
    Integer,
    DateTime,
    CheckConstraint,
    Index,
)
from sqlalchemy.orm import relationship
from app.database import Base


class AuctionStatus(str, Enum):
    UPCOMING = "UPCOMING"
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"
    FORCE_CLOSED = "FORCE_CLOSED"


class ExtensionTriggerType(str, Enum):
    BID_RECEIVED = "BID_RECEIVED"
    RANK_CHANGE = "RANK_CHANGE"
    L1_CHANGE = "L1_CHANGE"


class RFQ(Base):
    __tablename__ = "rfqs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    reference_id = Column(String(64), unique=True, nullable=False, index=True)
    rfq_name = Column(String(255), nullable=False, index=True)
    status = Column(String(32), nullable=False, default=AuctionStatus.ACTIVE.value, index=True)

    bid_start_time = Column(DateTime(timezone=True), nullable=False)
    bid_close_time = Column(DateTime(timezone=True), nullable=False, index=True)
    original_bid_close_time = Column(DateTime(timezone=True), nullable=False)
    forced_bid_close_time = Column(DateTime(timezone=True), nullable=False)
    pickup_service_date = Column(DateTime(timezone=True), nullable=False)

    british_auction_enabled = Column(Boolean, nullable=False, default=True)
    trigger_window_minutes = Column(Integer, nullable=False, default=10)
    extension_duration_minutes = Column(Integer, nullable=False, default=5)
    extension_trigger_type = Column(
        String(32),
        nullable=False,
        default=ExtensionTriggerType.BID_RECEIVED.value,
    )
    extension_count = Column(Integer, nullable=False, default=0)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    quotes = relationship("Quote", back_populates="rfq", cascade="all, delete-orphan", order_by="Quote.submitted_at.desc()")
    activity_logs = relationship("AuctionActivityLog", back_populates="rfq", cascade="all, delete-orphan", order_by="AuctionActivityLog.created_at.desc()")

    __table_args__ = (
        CheckConstraint("forced_bid_close_time >= bid_close_time", name="chk_forced_after_close"),
        CheckConstraint("bid_close_time > bid_start_time", name="chk_close_after_start"),
        CheckConstraint("trigger_window_minutes > 0", name="chk_positive_window"),
        CheckConstraint("extension_duration_minutes > 0", name="chk_positive_extension"),
        Index("idx_rfqs_status_close", "status", "bid_close_time"),
    )
