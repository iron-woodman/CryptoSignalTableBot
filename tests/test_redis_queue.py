from app_queue import redis_queue


class FakeRedis:
    def __init__(self):
        self.items = []

    def rpush(self, _queue_name, item):
        self.items.append(item)

    def lpop(self, _queue_name):
        if not self.items:
            return None
        return self.items.pop(0)


def _clear_fallback_queue():
    with redis_queue._fallback_lock:
        redis_queue._fallback_queue.clear()


def test_push_and_pop_use_redis_client(monkeypatch):
    _clear_fallback_queue()
    fake = FakeRedis()
    monkeypatch.setattr(redis_queue, "_get_client", lambda: fake)

    redis_queue.push({"chat_id": "1", "text": "hello"})
    item = redis_queue.pop()

    assert item == {"chat_id": "1", "text": "hello"}


def test_push_falls_back_to_memory_when_redis_fails(monkeypatch):
    _clear_fallback_queue()

    def boom():
        raise RuntimeError("redis down")

    monkeypatch.setattr(redis_queue, "_get_client", boom)

    redis_queue.push({"chat_id": "2", "text": "fallback"})
    item = redis_queue.pop()

    assert item == {"chat_id": "2", "text": "fallback"}


def test_pop_returns_none_when_empty(monkeypatch):
    _clear_fallback_queue()
    fake = FakeRedis()
    monkeypatch.setattr(redis_queue, "_get_client", lambda: fake)

    assert redis_queue.pop() is None
