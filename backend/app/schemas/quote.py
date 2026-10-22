from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, model_validator


class QuoteCreate(BaseModel):
    carrier_name: str = Field(..., min_length=2, max_length=128, description="Name of submitting carrier/supplier")
    freight_charges: Decimal = Field(..., ge=0, description="Freight cost component")
    origin_charges: Decimal = Field(..., ge=0, description="Origin charges component")
    destination_charges: Decimal = Field(..., ge=0, description="Destination charges component")
    transit_time_days: int = Field(..., gt=0, description="Committed transit duration in days")
    validity_date: datetime = Field(..., description="Validity period of quote")

    @model_validator(mode="after")
    def validate_positive_total(self):
        total = self.freight_charges + self.origin_charges + self.destination_charges
        if total <= 0:
            raise ValueError("Total quote price (freight + origin + destination) must be strictly greater than 0.")
        return self


class SupplierRankItem(BaseModel):
    carrier_name: str
    rank_label: str  # e.g. "L1", "L2", "L3"
    rank_number: int  # 1, 2, 3...
    best_price: Decimal
    quote_id: str
    submitted_at: datetime
    transit_time_days: int
    validity_date: datetime

    model_config = {"from_attributes": True}


class QuoteResponse(BaseModel):
    id: str
    rfq_id: str
    carrier_name: str
    freight_charges: Decimal
    origin_charges: Decimal
    destination_charges: Decimal
    total_price: Decimal
    transit_time_days: int
    validity_date: datetime
    submitted_at: datetime
    rank_at_submission: Optional[int] = None
    is_carrier_best: bool = True

    model_config = {"from_attributes": True}
