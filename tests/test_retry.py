import asyncio

from utils import retry as retry_module


def test_async_retry_succeeds_after_retries(monkeypatch):
    attempts = {"count": 0}
    sleep_calls = []

    async def fake_sleep(delay):
        sleep_calls.append(delay)

    async def flaky():
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise RuntimeError("temporary")
        return "ok"

    monkeypatch.setattr(retry_module.asyncio, "sleep", fake_sleep)

    result = asyncio.run(retry_module.async_retry(flaky, retries=5, base_delay=0.5))

    assert result == "ok"
    assert attempts["count"] == 3
    assert sleep_calls == [0.5, 1.0]


def test_async_retry_raises_after_max_retries(monkeypatch):
    sleep_calls = []

    async def fake_sleep(delay):
        sleep_calls.append(delay)

    async def always_fail():
        raise ValueError("fail")

    monkeypatch.setattr(retry_module.asyncio, "sleep", fake_sleep)

    try:
        asyncio.run(retry_module.async_retry(always_fail, retries=3, base_delay=1.0))
        assert False, "Expected RuntimeError"
    except RuntimeError as exc:
        assert "Max retries exceeded" in str(exc)

    assert sleep_calls == [1.0, 2.0, 4.0]
