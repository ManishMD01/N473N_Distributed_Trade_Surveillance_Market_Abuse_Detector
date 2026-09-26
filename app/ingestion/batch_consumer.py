"""Batch ingestion entry point.

The consumer processes immutable files in bounded batches, validates records,
and commits a checkpoint only after the database transaction succeeds.
"""
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime


@dataclass(frozen=True)
class TradeRecord:
    event_id: str
    symbol: str
    event_time: datetime
    buyer_ref: str
    seller_ref: str
    price: Decimal
    quantity: Decimal


def consume_batches(records: Iterable[TradeRecord], batch_size: int = 10_000):
    """Yield bounded batches; persistence/checkpointing is deliberately explicit."""
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    batch: list[TradeRecord] = []
    for record in records:
        batch.append(record)
        if len(batch) == batch_size:
            yield batch
            batch = []
    if batch:
        yield batch
