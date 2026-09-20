from types import SimpleNamespace

from app.services import data_retention


class _FakeSession:
    def __init__(self, outcomes, log):
        self._outcomes, self._log = outcomes, log

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def execute(self, stmt, params):
        self._log.append((str(stmt), params))
        return SimpleNamespace(rowcount=self._outcomes.pop(0))

    async def commit(self):
        pass


async def test_prune_deletes_in_batches_until_a_short_batch(monkeypatch):
    full = data_retention.DELETE_BATCH_ROWS
    log: list = []
    # ohlcv_1min: two full batches then a short one; breakout_events and analytics_events: one short batch each
    outcomes = [full, full, 7, 3, 5]
    monkeypatch.setattr(data_retention, "SessionLocal", lambda: _FakeSession(outcomes, log))
    order: list[str] = []

    async def _rollup(days_back, today):
        order.append("rollup")

    from app.services import analytics

    monkeypatch.setattr(analytics, "rollup_days", _rollup)

    async def _no_sleep(_):
        pass

    monkeypatch.setattr(data_retention.asyncio, "sleep", _no_sleep)

    result = await data_retention.prune_once()

    assert result == {"ohlcv_1min": 2 * full + 7, "breakout_events": 3, "analytics_events": 5}
    assert order == ["rollup"]  # daily totals are finalised before any raw analytics rows are deleted
    assert len(log) == 5
    assert "ohlcv_1min" in log[0][0] and "breakout_events" in log[3][0] and "analytics_events" in log[4][0]
    cutoffs = [entry[1]["cutoff"] for entry in log]
    assert cutoffs[0] > cutoffs[3]  # candles are kept 3 days, events 14: the candle cutoff is more recent
