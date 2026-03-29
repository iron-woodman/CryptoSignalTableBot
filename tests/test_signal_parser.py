from utils.tg_signal2 import parse_signal_data2


def test_parse_signal_data2_valid_message():
    text = (
        "🚀 #BTC/USDT [LONG]\n"
        "Entry: market\n"
        "Take-Profit:\n"
        "1) 101.1 (25%)\n"
        "2) 102.2 (25%)\n"
        "3) 103.3 (25%)\n"
        "Stop-loss: 95.5\n"
    )

    parsed = parse_signal_data2(text)

    assert parsed is not None
    assert parsed["coin"] == "BTC/USDT"
    assert parsed["side"] == "LONG"
    assert parsed["tp1"] == 101.1
    assert parsed["tp2"] == 102.2
    assert parsed["tp3"] == 103.3
    assert parsed["sl"] == 95.5


def test_parse_signal_data2_returns_none_for_invalid_message():
    text = "Random text without valid signal format"

    assert parse_signal_data2(text) is None
