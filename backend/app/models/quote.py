import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Boolean,
    Integer,
    Numeric,
    DateTime,
    ForeignKey,
    CheckConstraint,
    Index,
)
from sqlalchemy.orm import relationship
from app.database import Base


class Quote(Base):
    __tablename__ = "quotes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    rfq_id = Column(String(36), ForeignKey("rfqs.id", ondelete="CASCADE"), nullable=False, index=True)
    carrier_name = Column(String(128), nullable=False, index=True)

    freight_charges = Column(Numeric(12, 2), nullable=False)
    origin_charges = Column(Numeric(12, 2), nullable=False)
    destination_charges = Column(Numeric(12, 2), nullable=False)
    total_price = Column(Numeric(12, 2), nullable=False)

    transit_time_days = Column(Integer, nullable=False)
    validity_date = Column(DateTime(timezone=True), nullable=False)
    submitted_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    rank_at_submission = Column(Integer, nullable=True)
    is_carrier_best = Column(Boolean, nullable=False, default=True)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    rfq = relationship("RFQ", back_populates="quotes")

    __table_args__ = (
        CheckConstraint("freight_charges >= 0", name="chk_quote_freight_pos"),
        CheckConstraint("origin_charges >= 0", name="chk_quote_origin_pos"),
        CheckConstraint("destination_charges >= 0", name="chk_quote_dest_pos"),
        CheckConstraint("total_price >= 0", name="chk_quote_total_pos"),
        CheckConstraint("transit_time_days > 0", name="chk_quote_transit_pos"),
        Index("idx_quotes_rfq_price_time", "rfq_id", "total_price", "submitted_at"),
        Index("idx_quotes_rfq_carrier", "rfq_id", "carrier_name"),
    )
