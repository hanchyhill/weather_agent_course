"""L12 天气专线：工具与检查函数的验收用例（离线，不调用模型）。"""
from datetime import datetime

import pytest

from lessons_import import load_lesson_module
from weather_tools import weather as wx

wa = load_lesson_module("L12_天气查询专线", "weather_agent")
NOW = datetime(2026, 8, 11, 8, 30)


# ---- W1 地名
def test_geocode_unique():
    r = wx.geocode("广州天河区")
    assert r["status"] == "ok"
    c = r["candidates"][0]
    assert abs(c["lon"] - 113.36) < 0.1 and abs(c["lat"] - 23.12) < 0.1


def test_geocode_ambiguous():
    r = wx.geocode("朝阳区")
    assert r["status"] == "ambiguous" and len(r["candidates"]) == 2


def test_geocode_not_found():
    assert wx.geocode("火星基地")["status"] == "not_found"
    assert wx.geocode("")["status"] == "not_found"


# ---- W2 / W3 数据
def test_history_yesterday_utc_window():
    r = wx.query_station_history(113.36, 23.12, "2026-08-09 16:00:00", "2026-08-10 15:00:00")
    assert r["status"] == "ok" and r["count"] == 24
    assert r["summary"]["rain_total_mm"] == pytest.approx(19.9, abs=0.05)


def test_history_future_is_no_data():
    r = wx.query_station_history(113.36, 23.12, "2026-08-12 00:00:00", "2026-08-12 23:00:00")
    assert r["status"] == "no_data" and "最新实况" in r["message"]


def test_history_far_away_no_station():
    assert wx.query_station_history(116.4, 39.9, "2026-08-10 00:00:00", "2026-08-10 01:00:00")["status"] == "no_station"


def test_forecast_tomorrow():
    r = wx.query_forecast(113.36, 23.12, "2026-08-11 16:00:00", "2026-08-12 15:00:00")
    assert r["status"] == "ok" and r["count"] == 24
    assert r["summary"]["rain_total_mm"] == pytest.approx(45.4, abs=0.05)


def test_forecast_past_is_no_data():
    r = wx.query_forecast(113.36, 23.12, "2026-08-10 00:00:00", "2026-08-10 23:00:00")
    assert r["status"] == "no_data"


def test_bad_time_format():
    with pytest.raises(ValueError):
        wx.query_forecast(113.36, 23.12, "2026-08-11", "2026-08-12")
    with pytest.raises(ValueError):
        wx.query_forecast(113.36, 23.12, "2026-08-12 00:00:00", "2026-08-11 00:00:00")


def test_today_split_has_no_gap():
    """今天：实况到 UTC 00 时，预报从 UTC 01 时起，合起来正好覆盖北京时 00～23 时。"""
    h = wx.query_station_history(113.36, 23.12, "2026-08-10 16:00:00", "2026-08-11 00:00:00")
    f = wx.query_forecast(113.36, 23.12, "2026-08-11 01:00:00", "2026-08-11 15:00:00")
    assert h["count"] + f["count"] == 24


# ---- W5 北京时
def test_bj_to_utc_and_cross_month():
    assert wx.bj_range_to_utc("2026-08-10 00:00:00", "2026-08-10 23:00:00") == (
        "2026-08-09 16:00:00", "2026-08-10 15:00:00")
    assert wx.bj_range_to_utc("2026-08-01 00:00:00", "2026-08-01 07:00:00")[0] == "2026-07-31 16:00:00"


def test_bj_tool_matches_utc_tool():
    import json
    bj = json.loads(wa.get_station_history_bj.invoke(
        {"lon": 113.36, "lat": 23.12, "start_time": "2026-08-10 00:00:00", "end_time": "2026-08-10 23:00:00"}))
    utc = wx.query_station_history(113.36, 23.12, "2026-08-09 16:00:00", "2026-08-10 15:00:00")
    assert bj["summary"] == utc["summary"]
    assert bj["rows"][0]["time_bj"] == "2026-08-10 00:00:00"


# ---- 检查函数
def test_expected_windows():
    e = wa.expected_windows(NOW)
    assert e["yesterday"]["history"] == ("2026-08-09 16:00:00", "2026-08-10 15:00:00")
    assert e["today"]["history"] == ("2026-08-10 16:00:00", "2026-08-11 00:00:00")
    assert e["today"]["forecast"] == ("2026-08-11 01:00:00", "2026-08-11 15:00:00")
    assert e["tomorrow"]["forecast"] == ("2026-08-11 16:00:00", "2026-08-12 15:00:00")


def _calls(*specs):
    return [{"name": n, "args": a} for n, a in specs]


GEO = ("geocode_place", {"place": "广州天河区"})


def test_check_calls_today_missing_history():
    calls = _calls(GEO, ("get_forecast", {"lon": 1, "lat": 1, "start_time": "2026-08-11 01:00:00",
                                         "end_time": "2026-08-11 15:00:00"}))
    p = wa.check_calls(calls, wa.expected_windows(NOW)["today"],
                       hist_tool="get_station_history", fore_tool="get_forecast")
    assert any("漏调" in x for x in p)


def test_check_calls_forgot_timezone():
    calls = _calls(GEO, ("get_station_history", {"lon": 1, "lat": 1, "start_time": "2026-08-10 00:00:00",
                                                "end_time": "2026-08-10 23:00:00"}))
    p = wa.check_calls(calls, wa.expected_windows(NOW)["yesterday"],
                       hist_tool="get_station_history", fore_tool="get_forecast")
    assert any("窗口不对" in x for x in p)


def test_check_calls_ok_and_bj():
    calls = _calls(GEO, ("get_station_history_bj", {"lon": 1, "lat": 1, "start_time": "2026-08-10 00:00:00",
                                                   "end_time": "2026-08-10 23:00:00"}))
    assert wa.check_calls(calls, wa.expected_windows(NOW)["yesterday"], hist_tool="get_station_history_bj",
                          fore_tool="get_forecast_bj", bj_args=True) == []


def test_check_calls_unneeded_tool_and_no_geocode():
    calls = _calls(("get_forecast", {"lon": 1, "lat": 1, "start_time": "x", "end_time": "y"}))
    p = wa.check_calls(calls, wa.expected_windows(NOW)["yesterday"],
                       hist_tool="get_station_history", fore_tool="get_forecast")
    assert any("不该调用" in x for x in p) and any("经纬度" in x for x in p)
