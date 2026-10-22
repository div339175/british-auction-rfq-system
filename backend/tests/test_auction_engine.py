from datetime import datetime, timezone, timedelta
from decimal import Decimal
import pytest
from app.engine.auction_engine import BritishAuctionEngine, CarrierBidEntry
from app.models.rfq import ExtensionTriggerType


@pytest.fixture
def base_auction_times():
    base = datetime(2026, 10, 22, 18, 0, 0, tzinfo=timezone.utc)
    return {
        "start": base - timedelta(hours=2),        # 16:00
        "close": base,                             # 18:00
        "forced_close": base + timedelta(minutes=10) # 18:10
    }


def test_bid_outside_trigger_window(base_auction_times):
    """Bid placed at 17:45 (before 17:50 trigger start) should be valid but NOT extend."""
    bid_time = base_auction_times["close"] - timedelta(minutes=15)  # 17:45
    result = BritishAuctionEngine.evaluate_bid_submission(
        bid_time=bid_time,
        bid_start_time=base_auction_times["start"],
        current_close_time=base_auction_times["close"],
        forced_close_time=base_auction_times["forced_close"],
        british_auction_enabled=True,
        trigger_window_minutes=10,
        extension_duration_minutes=5,
        trigger_type=ExtensionTriggerType.BID_RECEIVED,
        existing_carrier_bids=[],
        new_carrier_name="Carrier Alpha",
        new_total_price=Decimal("100000.00"),
        new_quote_id="q1",
    )
    assert result.is_valid is True
    assert result.is_in_trigger_window is False
    assert result.should_extend is False
    assert result.new_close_time == base_auction_times["close"]
    assert result.new_l1 == "Carrier Alpha"


def test_normal_extension_bid_received(base_auction_times):
    """Bid placed at 17:55 (within 10m window) should extend close time from 18:00 to 18:05."""
    bid_time = base_auction_times["close"] - timedelta(minutes=5)  # 17:55
    result = BritishAuctionEngine.evaluate_bid_submission(
        bid_time=bid_time,
        bid_start_time=base_auction_times["start"],
        current_close_time=base_auction_times["close"],
        forced_close_time=base_auction_times["forced_close"],
        british_auction_enabled=True,
        trigger_window_minutes=10,
        extension_duration_minutes=5,
        trigger_type=ExtensionTriggerType.BID_RECEIVED,
        existing_carrier_bids=[],
        new_carrier_name="Carrier Alpha",
        new_total_price=Decimal("95000.00"),
        new_quote_id="q1",
    )
    assert result.is_valid is True
    assert result.is_in_trigger_window is True
    assert result.should_extend is True
    assert result.new_close_time == datetime(2026, 10, 22, 18, 5, 0, tzinfo=timezone.utc)
    assert result.is_capped is False


def test_boundary_bid_at_exact_close_time(base_auction_times):
    """Bid placed at exactly 18:00:00 should be rejected because auction has closed."""
    bid_time = base_auction_times["close"]  # 18:00:00
    result = BritishAuctionEngine.evaluate_bid_submission(
        bid_time=bid_time,
        bid_start_time=base_auction_times["start"],
        current_close_time=base_auction_times["close"],
        forced_close_time=base_auction_times["forced_close"],
        british_auction_enabled=True,
        trigger_window_minutes=10,
        extension_duration_minutes=5,
        trigger_type=ExtensionTriggerType.BID_RECEIVED,
        existing_carrier_bids=[],
        new_carrier_name="Carrier Alpha",
        new_total_price=Decimal("95000.00"),
        new_quote_id="q1",
    )
    assert result.is_valid is False
    assert "Auction closed" in result.error_message


def test_bid_after_forced_close(base_auction_times):
    """Bid placed after forced close (18:11) must be rejected."""
    bid_time = base_auction_times["forced_close"] + timedelta(minutes=1)
    result = BritishAuctionEngine.evaluate_bid_submission(
        bid_time=bid_time,
        bid_start_time=base_auction_times["start"],
        current_close_time=base_auction_times["forced_close"],
        forced_close_time=base_auction_times["forced_close"],
        british_auction_enabled=True,
        trigger_window_minutes=10,
        extension_duration_minutes=5,
        trigger_type=ExtensionTriggerType.BID_RECEIVED,
        existing_carrier_bids=[],
        new_carrier_name="Carrier Alpha",
        new_total_price=Decimal("95000.00"),
        new_quote_id="q1",
    )
    assert result.is_valid is False
    assert "Auction closed" in result.error_message or "forced close" in result.error_message


def test_extension_clamped_to_forced_close(base_auction_times):
    """
    If current close is 18:08 and forced close is 18:10, a 5-minute extension would be 18:13,
    which must be capped strictly at 18:10.
    """
    current_close = datetime(2026, 10, 22, 18, 8, 0, tzinfo=timezone.utc)
    bid_time = datetime(2026, 10, 22, 18, 5, 0, tzinfo=timezone.utc)  # within 10m window (17:58 - 18:08)
    
    result = BritishAuctionEngine.evaluate_bid_submission(
        bid_time=bid_time,
        bid_start_time=base_auction_times["start"],
        current_close_time=current_close,
        forced_close_time=base_auction_times["forced_close"],  # 18:10
        british_auction_enabled=True,
        trigger_window_minutes=10,
        extension_duration_minutes=5,
        trigger_type=ExtensionTriggerType.BID_RECEIVED,
        existing_carrier_bids=[],
        new_carrier_name="Carrier Alpha",
        new_total_price=Decimal("95000.00"),
        new_quote_id="q1",
    )
    assert result.is_valid is True
    assert result.should_extend is True
    assert result.new_close_time == datetime(2026, 10, 22, 18, 10, 0, tzinfo=timezone.utc)
    assert result.is_capped is True
    assert "clamped to forced close deadline" in result.extension_reason


def test_multiple_extensions_cannot_exceed_forced_close(base_auction_times):
    """
    Simulate successive extensions:
    18:00 -> 18:05 -> 18:10 (forced close) -> cannot extend further.
    """
    # 1. First bid at 17:58 -> extends from 18:00 to 18:05
    res1 = BritishAuctionEngine.evaluate_bid_submission(
        bid_time=datetime(2026, 10, 22, 17, 58, 0, tzinfo=timezone.utc),
        bid_start_time=base_auction_times["start"],
        current_close_time=base_auction_times["close"], # 18:00
        forced_close_time=base_auction_times["forced_close"], # 18:10
        british_auction_enabled=True,
        trigger_window_minutes=10,
        extension_duration_minutes=5,
        trigger_type=ExtensionTriggerType.BID_RECEIVED,
        existing_carrier_bids=[],
        new_carrier_name="Carrier A",
        new_total_price=Decimal("95000.00"),
        new_quote_id="q1",
    )
    assert res1.new_close_time == datetime(2026, 10, 22, 18, 5, 0, tzinfo=timezone.utc)

    # 2. Second bid at 18:02 (trigger window for 18:05 is 17:55 - 18:05) -> extends from 18:05 to 18:10
    res2 = BritishAuctionEngine.evaluate_bid_submission(
        bid_time=datetime(2026, 10, 22, 18, 2, 0, tzinfo=timezone.utc),
        bid_start_time=base_auction_times["start"],
        current_close_time=res1.new_close_time, # 18:05
        forced_close_time=base_auction_times["forced_close"], # 18:10
        british_auction_enabled=True,
        trigger_window_minutes=10,
        extension_duration_minutes=5,
        trigger_type=ExtensionTriggerType.BID_RECEIVED,
        existing_carrier_bids=[CarrierBidEntry("Carrier A", Decimal("95000.00"), res1.previous_close_time, "q1")],
        new_carrier_name="Carrier B",
        new_total_price=Decimal("94000.00"),
        new_quote_id="q2",
    )
    assert res2.new_close_time == datetime(2026, 10, 22, 18, 10, 0, tzinfo=timezone.utc)
    assert res2.is_capped is False

    # 3. Third bid at 18:07 (trigger window for 18:10 is 18:00 - 18:10) -> cannot extend beyond 18:10!
    res3 = BritishAuctionEngine.evaluate_bid_submission(
        bid_time=datetime(2026, 10, 22, 18, 7, 0, tzinfo=timezone.utc),
        bid_start_time=base_auction_times["start"],
        current_close_time=res2.new_close_time, # 18:10 (at forced close limit)
        forced_close_time=base_auction_times["forced_close"], # 18:10
        british_auction_enabled=True,
        trigger_window_minutes=10,
        extension_duration_minutes=5,
        trigger_type=ExtensionTriggerType.BID_RECEIVED,
        existing_carrier_bids=[
            CarrierBidEntry("Carrier B", Decimal("94000.00"), res2.previous_close_time, "q2"),
            CarrierBidEntry("Carrier A", Decimal("95000.00"), res1.previous_close_time, "q1"),
        ],
        new_carrier_name="Carrier C",
        new_total_price=Decimal("93000.00"),
        new_quote_id="q3",
    )
    assert res3.is_valid is True
    assert res3.should_extend is False  # Cannot extend past 18:10
    assert res3.new_close_time == datetime(2026, 10, 22, 18, 10, 0, tzinfo=timezone.utc)
    assert res3.is_capped is True


def test_rank_change_trigger(base_auction_times):
    """
    Under RANK_CHANGE mode:
    Existing: A = 100k (L1), B = 110k (L2)
    Carrier C bids 105k:
      New order: A (L1), C (L2), B (L3).
      Rank changed! (B went from L2 to L3)
      Even though L1 didn't change, RANK_CHANGE triggers extension.
    """
    existing = [
        CarrierBidEntry("Carrier A", Decimal("100000.00"), base_auction_times["start"], "q1"),
        CarrierBidEntry("Carrier B", Decimal("110000.00"), base_auction_times["start"], "q2"),
    ]
    bid_time = base_auction_times["close"] - timedelta(minutes=5) # 17:55
    res = BritishAuctionEngine.evaluate_bid_submission(
        bid_time=bid_time,
        bid_start_time=base_auction_times["start"],
        current_close_time=base_auction_times["close"],
        forced_close_time=base_auction_times["forced_close"],
        british_auction_enabled=True,
        trigger_window_minutes=10,
        extension_duration_minutes=5,
        trigger_type=ExtensionTriggerType.RANK_CHANGE,
        existing_carrier_bids=existing,
        new_carrier_name="Carrier C",
        new_total_price=Decimal("105000.00"),
        new_quote_id="q3",
    )
    assert res.is_valid is True
    assert res.rank_changed is True
    assert res.l1_changed is False
    assert res.should_extend is True
    assert res.new_close_time == base_auction_times["close"] + timedelta(minutes=5)


def test_l1_change_trigger_only_on_l1(base_auction_times):
    """
    Under L1_CHANGE mode:
    Existing: A = 100k (L1), B = 110k (L2)
    Case 1: Carrier C bids 105k -> ranks L2. L1 is STILL Carrier A.
            Extension should NOT occur!
    Case 2: Carrier D bids 95k -> ranks L1. L1 changed from A to D.
            Extension MUST occur!
    """
    existing = [
        CarrierBidEntry("Carrier A", Decimal("100000.00"), base_auction_times["start"], "q1"),
        CarrierBidEntry("Carrier B", Decimal("110000.00"), base_auction_times["start"], "q2"),
    ]
    bid_time = base_auction_times["close"] - timedelta(minutes=5)

    # Case 1: C bids 105k (L2) -> No L1 change -> No extension
    res_no_ext = BritishAuctionEngine.evaluate_bid_submission(
        bid_time=bid_time,
        bid_start_time=base_auction_times["start"],
        current_close_time=base_auction_times["close"],
        forced_close_time=base_auction_times["forced_close"],
        british_auction_enabled=True,
        trigger_window_minutes=10,
        extension_duration_minutes=5,
        trigger_type=ExtensionTriggerType.L1_CHANGE,
        existing_carrier_bids=existing,
        new_carrier_name="Carrier C",
        new_total_price=Decimal("105000.00"),
        new_quote_id="q3",
    )
    assert res_no_ext.is_valid is True
    assert res_no_ext.rank_changed is True
    assert res_no_ext.l1_changed is False
    assert res_no_ext.should_extend is False
    assert res_no_ext.new_close_time == base_auction_times["close"]

    # Case 2: D bids 95k (L1) -> L1 changed -> Extension occurs!
    res_ext = BritishAuctionEngine.evaluate_bid_submission(
        bid_time=bid_time,
        bid_start_time=base_auction_times["start"],
        current_close_time=base_auction_times["close"],
        forced_close_time=base_auction_times["forced_close"],
        british_auction_enabled=True,
        trigger_window_minutes=10,
        extension_duration_minutes=5,
        trigger_type=ExtensionTriggerType.L1_CHANGE,
        existing_carrier_bids=existing,
        new_carrier_name="Carrier D",
        new_total_price=Decimal("95000.00"),
        new_quote_id="q4",
    )
    assert res_ext.is_valid is True
    assert res_ext.l1_changed is True
    assert res_ext.should_extend is True
    assert res_ext.new_close_time == base_auction_times["close"] + timedelta(minutes=5)


def test_higher_price_from_same_carrier_rejected(base_auction_times):
    """If Carrier A already bid 95k, submitting 98k must be rejected as uncompetitive."""
    existing = [CarrierBidEntry("Carrier A", Decimal("95000.00"), base_auction_times["start"], "q1")]
    res = BritishAuctionEngine.evaluate_bid_submission(
        bid_time=base_auction_times["close"] - timedelta(minutes=5),
        bid_start_time=base_auction_times["start"],
        current_close_time=base_auction_times["close"],
        forced_close_time=base_auction_times["forced_close"],
        british_auction_enabled=True,
        trigger_window_minutes=10,
        extension_duration_minutes=5,
        trigger_type=ExtensionTriggerType.BID_RECEIVED,
        existing_carrier_bids=existing,
        new_carrier_name="Carrier A",
        new_total_price=Decimal("98000.00"),
        new_quote_id="q2",
    )
    assert res.is_valid is False
    assert "not lower than carrier's existing best quote" in res.error_message


def test_bid_before_auction_start_rejected(base_auction_times):
    """Bid placed prior to auction start time must be rejected."""
    bid_time = base_auction_times["start"] - timedelta(minutes=1)
    res = BritishAuctionEngine.evaluate_bid_submission(
        bid_time=bid_time,
        bid_start_time=base_auction_times["start"],
        current_close_time=base_auction_times["close"],
        forced_close_time=base_auction_times["forced_close"],
        british_auction_enabled=True,
        trigger_window_minutes=10,
        extension_duration_minutes=5,
        trigger_type=ExtensionTriggerType.BID_RECEIVED,
        existing_carrier_bids=[],
        new_carrier_name="Carrier A",
        new_total_price=Decimal("95000.00"),
        new_quote_id="q1",
    )
    assert res.is_valid is False
    assert "before auction start time" in res.error_message


def test_tie_breaking_favors_earlier_timestamp(base_auction_times):
    """When two carriers bid the exact same price, the earlier one retains the higher rank (L1)."""
    t1 = base_auction_times["start"] + timedelta(minutes=10)
    t2 = base_auction_times["start"] + timedelta(minutes=20)
    existing = [CarrierBidEntry("Carrier A", Decimal("95000.00"), t1, "q1")]
    res = BritishAuctionEngine.evaluate_bid_submission(
        bid_time=t2,
        bid_start_time=base_auction_times["start"],
        current_close_time=base_auction_times["close"],
        forced_close_time=base_auction_times["forced_close"],
        british_auction_enabled=True,
        trigger_window_minutes=10,
        extension_duration_minutes=5,
        trigger_type=ExtensionTriggerType.BID_RECEIVED,
        existing_carrier_bids=existing,
        new_carrier_name="Carrier B",
        new_total_price=Decimal("95000.00"),
        new_quote_id="q2",
    )
    assert res.is_valid is True
    # Carrier A remains L1 because t1 < t2
    assert res.new_l1 == "Carrier A"
    assert res.new_ranking[0][0] == "Carrier A"
    assert res.new_ranking[1][0] == "Carrier B"
