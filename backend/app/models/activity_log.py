import uuid
from datetime import datetime, timezone
from enum import Enum
from sqlalchemy import (
    Column,
    String,
    DateTime,
    Text,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import relationship
from app.database import Base


class ActivityEventType(str, Enum):
    RFQ_CREATED = "RFQ_CREATED"
    BID_SUBMITTED = "BID_SUBMITTED"
    AUCTION_EXTENDED = "AUCTION_EXTENDED"
    EXTENSION_CAPPED = "EXTENSION_CAPPED"
    AUCTION_CLOSED = "AUCTION_CLOSED"
    AUCTION_FORCE_CLOSED = "AUCTION_FORCE_CLOSED"


class AuctionActivityLog(Base):
    __tablename__ = "auction_activity_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    rfq_id = Column(String(36), ForeignKey("rfqs.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(32), nullable=False)

    carrier_name = Column(String(128), nullable=True)
    quote_id = Column(String(36), nullable=True)

    previous_close_time = Column(DateTime(timezone=True), nullable=True)
    new_close_time = Column(DateTime(timezone=True), nullable=True)

    message = Column(Text, nullable=False)
    metadata_json = Column(Text, nullable=True)  # JSON-encoded string for cross-database compatibility

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    # Relationships
    rfq = relationship("RFQ", back_populates="activity_logs")

    __table_args__ = (
        Index("idx_logs_rfq_created", "rfq_id", "created_at"),
    )
