from utils import tg_signal


def test_send_alert_queues_html_message(monkeypatch):
    calls = []

    def fake_push_message(chat_id, text, parse_mode=None):
        calls.append({"chat_id": chat_id, "text": text, "parse_mode": parse_mode})

    monkeypatch.setattr(tg_signal, "push_message", fake_push_message)
    monkeypatch.setattr(tg_signal, "CHAT_ID", "-100-main")

    tg_signal.send_alert("<b>TP hit</b>")

    assert calls == [{"chat_id": "-100-main", "text": "<b>TP hit</b>", "parse_mode": "HTML"}]


def test_send_av_alert_uses_av_channel_or_main(monkeypatch):
    calls = []

    def fake_push_message(chat_id, text, parse_mode=None):
        calls.append({"chat_id": chat_id, "text": text, "parse_mode": parse_mode})

    monkeypatch.setattr(tg_signal, "push_message", fake_push_message)
    monkeypatch.setattr(tg_signal, "CHAT_ID", "-100-main")
    monkeypatch.setattr(tg_signal, "AV_CHAT_ID", "-100-av")

    tg_signal.send_av_alert("avg hit")

    assert calls == [{"chat_id": "-100-av", "text": "avg hit", "parse_mode": None}]
