from lessons_import import load_lesson_module

w = load_lesson_module("L04_文本类工具", "03_备选_陆地大风工具")


def test_same_start_end_shifts_3h():
    assert w.normalize_range("2026-08-11 08:00:00", "2026-08-11 08:00:00") == (
        "2026-08-11 05:00:00", "2026-08-11 08:00:00")


def test_sentence():
    assert w.build_sentence(w.SAMPLE) == (
        "我省陆地上湛江市徐闻录得全省最大平均风15.2m/s，阳江市海陵岛录得全省最大阵风24.6m/s。")


def test_failed_status():
    assert w.build_sentence({"status": 0}) == "大风数据查询失败。"
