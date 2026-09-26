from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.ingestion.batch_consumer import TradeRecord, consume_batches


def record(i: int) -> TradeRecord:
    return TradeRecord(str(i), "ABC", datetime.now(timezone.utc), "buyer", "seller", Decimal("1"), Decimal("2"))


def test_consumer_yields_bounded_batches_and_remainder():
    batches = list(consume_batches((record(i) for i in range(5)), batch_size=2))
    assert [len(batch) for batch in batches] == [2, 2, 1]


def test_consumer_rejects_invalid_batch_size():
    with pytest.raises(ValueError):
        list(consume_batches([], batch_size=0))
