import httpx
import pytest

from app.main import app
from app.utils.redis_keys import indicator_key


@pytest.mark.usefixtures("fake_redis")
async def test_indicators_reads_the_daily_hash_the_poller_writes(fake_redis):
    await fake_redis.hset(
        indicator_key("RELIANCE", "1d"),
        mapping={"rsi_14": "61.25", "ema_9": "1250.5", "macd": "-1.2", "adx_14": "nan-junk"},
    )
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        resp = await c.get("/api/prices/indicators/reliance")

    assert resp.status_code == 200
    body = resp.json()
    assert body["symbol"] == "RELIANCE"
    assert body["rsi_14"] == 61.25
    assert body["ema_9"] == 1250.5
    assert body["adx_14"] is None  # unparseable value degrades to null, not a 500


@pytest.mark.usefixtures("fake_redis")
async def test_indicators_404_when_symbol_has_no_hash():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        resp = await c.get("/api/prices/indicators/NOPE")
    assert resp.status_code == 404
