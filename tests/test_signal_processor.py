from core import signal_processor


def test_format_signal_from_dict_orders_targets():
    payload = {
        "coin": "BTCUSDT",
        "side": "LONG",
        "tp2": 102.0,
        "tp1": 101.0,
        "sl": 99.5,
    }

    text = signal_processor.format_signal(payload)

    assert "Signal: BTCUSDT LONG" in text
    assert "TP: 101.0, 102.0" in text
    assert "SL: 99.5" in text


def test_push_message_builds_payload(monkeypatch):
    pushed = []

    def fake_push(data):
        pushed.append(data)

    monkeypatch.setattr(signal_processor, "push", fake_push)

    signal_processor.push_message(chat_id="-1001", text="hello", parse_mode="HTML")

    assert pushed == [{"chat_id": "-1001", "text": "hello", "parse_mode": "HTML"}]


def test_process_signal_uses_default_chat_id(monkeypatch):
    pushed = []

    def fake_push(data):
        pushed.append(data)

    monkeypatch.setattr(signal_processor, "push", fake_push)
    monkeypatch.setattr(signal_processor, "CHAT_ID", "-100-default")

    signal_processor.process_signal({"coin": "ETHUSDT", "side": "SHORT", "tp1": 10, "sl": 20})

    assert pushed
    assert pushed[0]["chat_id"] == "-100-default"
    assert pushed[0]["text"].startswith("Signal: ETHUSDT SHORT")
