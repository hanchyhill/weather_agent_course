"""L5 时间工具的验收用例。"""
from datetime import datetime

import pytest

from common.clock import BJ_TZ
from weather_tools import timeutil


@pytest.mark.parametrize("now, expected", [
    ("2025-06-14 00:00", "2025061312"),
    ("2025-06-14 05:59", "2025061312"),
    ("2025-06-14 06:00", "2025061400"),  # 切到当天 08 时次
    ("2025-06-14 13:59", "2025061400"),
    ("2025-06-14 14:00", "2025061412"),  # 切到当天 20 时次
    ("2025-06-14 23:59", "2025061412"),
    ("2025-06-15 00:00", "2025061412"),
    ("2025-01-01 03:00", "2024123112"),  # 跨年
])
def test_latest_init_time(now, expected):
    dt = datetime.strptime(now, "%Y-%m-%d %H:%M").replace(tzinfo=BJ_TZ)
    assert timeutil.latest_init_time(dt) == expected


def test_ecmwf_init_to_utc():
    assert timeutil.ecmwf_init_to_utc("2025061320", "UTC+8") == "2025061312"
    with pytest.raises(ValueError):
        timeutil.ecmwf_init_to_utc("2025061314", "UTC+8")


def test_lead_time_for():
    # 北京时 6 月 15 日 14 时：00 UTC 起报为 30 小时，前一天 12 UTC 起报为 42 小时
    assert timeutil.lead_time_for("2025061400", "2025-06-15 14:00") == 30
    assert timeutil.lead_time_for("2025061312", "2025-06-15 14:00") == 42


def test_lead_time_table_first_rows():
    rows = timeutil.lead_time_table("2025121612", max_hours=12)
    assert rows[0] == {"lead_time": 0, "utc": "2025-12-16 12:00", "bj": "2025-12-16 20:00"}
    assert rows[-1]["bj"] == "2025-12-17 08:00"
