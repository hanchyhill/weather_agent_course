"""台风专线 T2～T6 的验收用例（参考答案的测试）。

学员在 L5 自己写测试时，可以拿这份对照。
"""
import pytest

from weather_tools import typhoon


# T2：时区换算交给程序
@pytest.mark.parametrize("value, tz, expected_bj_key", [
    ("2026-08-11 08:00:00", "UTC+8", "2026-08-11 08:00:00"),
    ("2026-08-11 00:00:00", "UTC", "2026-08-11 08:00:00"),
])
def test_query_typhoon_converts_timezone(value, tz, expected_bj_key):
    expected = typhoon.request_getyphdata(expected_bj_key)
    assert typhoon.query_typhoon(value, tz) == expected


def test_query_typhoon_rejects_bad_format():
    with pytest.raises(ValueError):
        typhoon.query_typhoon("2026-08-11 08:00", "UTC+8")


def test_utc_only_tool_gets_wrong_answer_if_model_passes_bj():
    # T1 的坑：把北京时 08 时直接当世界时传入，实际查的是北京时 16 时
    wrong = typhoon.query_typhoon_utc("2026-08-11 08:00:00")
    right = typhoon.query_typhoon_utc("2026-08-11 00:00:00")
    assert typhoon.extract_systems(wrong) == []
    assert len(typhoon.extract_systems(right)) == 2


# T4：四种情形
def test_lookback_hit_first_try():
    r = typhoon.query_typhoon_with_lookback("2026-08-11 08:00:00")
    assert r["tsid"] == [547, 550]
    assert r["query_metadata"]["lookback_hours"] == 0
    assert r["query_metadata"]["fallback_used"] is False


def test_lookback_hit_after_21_hours():
    # 真实个例：2026-07-29 08:00 查询，回查到 7-28 11:00 才有红霞
    r = typhoon.query_typhoon_with_lookback("2026-07-29 08:00:00")
    meta = r["query_metadata"]
    assert meta["actual_datetime_bj"] == "2026-07-28 11:00:00"
    assert meta["lookback_hours"] == 21
    assert [a["offset_hours"] for a in meta["query_attempts"]] == list(range(0, 22, 3))


def test_lookback_none_within_24_hours():
    r = typhoon.query_typhoon_with_lookback("2026-07-23 08:00:00")
    assert r["status"] == "not_applicable"
    assert [a["offset_hours"] for a in r["query_attempts"]] == list(range(0, 25, 3))
    assert "不应请求依赖 tsid" in r["message"]


def test_lookback_unknown_shape_returned_as_is():
    r = typhoon.query_typhoon_with_lookback("2026-09-01 08:00:00")
    assert r == {"status": 0, "msg": "service busy"}


def test_lookback_accepts_utc():
    r = typhoon.query_typhoon_with_lookback("2026-08-11 00:00:00", "UTC")
    assert r["query_metadata"]["requested_datetime_bj"] == "2026-08-11 08:00:00"


# T5：路径图时次
def test_track_candidates_order():
    assert typhoon.track_candidates("2024-09-04 02:00:00") == [
        "2024-09-04 02:00:00", "2024-09-04 08:00:00", "2024-09-03 20:00:00",
    ]


def test_track_image_found_directly():
    path, used, fallback = typhoon.track_image_path("736", "2024-09-03 08:00:00")
    assert path.name == "736_2024090300.png"
    assert used == "2024-09-03 08:00:00" and fallback is False


def test_track_image_falls_back_when_missing():
    # 离线数据故意缺 736_2024090318（北京时 9 月 4 日 02 时）
    path, used, fallback = typhoon.track_image_path("736", "2024-09-04 02:00:00")
    assert path.name == "736_2024090400.png"
    assert used == "2024-09-04 08:00:00" and fallback is True


# T6：两套编号
def test_diagnostic_tsid_doc_example():
    assert typhoon.resolve_diagnostic_tsid("554") == "803"


def test_diagnostic_tsid_unknown_has_clear_message():
    with pytest.raises(LookupError, match="两套编号"):
        typhoon.resolve_diagnostic_tsid("999")
