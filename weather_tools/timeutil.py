"""时间换算工具（纯 Python，不调用模型）。

规则来源：
- latest_init_time：全项目统一用 agent_dev `src/tools/ToolBase.py:64-73` 的起报时次规则
- 其余：huishang_demo 的 src/tools/ecmwf_tools.py（convert_ecmwf_init_time_to_utc /
  get_available_forecast_lead_times）与 src/tools/typhoon_tools.py（_convert_datetime_timezone）
"""
from datetime import datetime, timedelta
from typing import Literal

Tz = Literal["UTC+8", "UTC"]


def convert_tz(value: str, fmt: str, src: Tz, dst: Tz) -> str:
    """在北京时（UTC+8）和世界时（UTC）之间换算。格式不对直接报错。"""
    if src not in ("UTC+8", "UTC") or dst not in ("UTC+8", "UTC"):
        raise ValueError(f"时区只能是 'UTC+8' 或 'UTC'，实际: {src} -> {dst}")
    try:
        dt = datetime.strptime(value, fmt)
    except ValueError as exc:
        raise ValueError(f"时间格式错误，应为 {fmt}，实际: {value}") from exc
    if src == "UTC+8" and dst == "UTC":
        dt -= timedelta(hours=8)
    elif src == "UTC" and dst == "UTC+8":
        dt += timedelta(hours=8)
    return dt.strftime(fmt)


def ecmwf_init_to_utc(init_time: str, timezone: Tz = "UTC") -> str:
    """ECMWF 起报时间转为 UTC（YYYYMMDDHH），并检查只能是 00 / 12 UTC。"""
    utc = convert_tz(init_time, "%Y%m%d%H", timezone, "UTC")
    if utc[-2:] not in ("00", "12"):
        raise ValueError(f"ECMWF 起报时次只能是 00/12 UTC（北京时 08/20），实际 UTC: {utc}")
    return utc


def latest_init_time(now_bj: datetime) -> str:
    """按资料到达经验，返回当前可用的最新 ECMWF 起报时次（UTC，YYYYMMDDHH）。

    规则与 agent_dev `src/tools/ToolBase.py:64-73` 完全一致（北京时）：
    - 北京时 14:00～23:59 用当天 12 UTC（北京 20 时次）
    - 北京时 06:00～13:59 用当天 00 UTC（北京 08 时次）
    - 北京时 00:00～05:59 用前一天 12 UTC（前一天北京 20 时次）
    """
    hour = now_bj.hour
    if hour >= 14:
        return now_bj.strftime("%Y%m%d") + "12"
    if hour >= 6:
        return now_bj.strftime("%Y%m%d") + "00"
    return (now_bj - timedelta(days=1)).strftime("%Y%m%d") + "12"


def lead_time_table(init_time_utc: str, max_hours: int = 240, step: int = 6) -> list[dict]:
    """列出每个预报时效对应的 UTC 时间和北京时。"""
    init_dt = datetime.strptime(init_time_utc, "%Y%m%d%H")
    rows = []
    for lead in range(0, max_hours + 1, step):
        utc_dt = init_dt + timedelta(hours=lead)
        rows.append({
            "lead_time": lead,
            "utc": utc_dt.strftime("%Y-%m-%d %H:%M"),
            "bj": (utc_dt + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M"),
        })
    return rows


def lead_time_for(init_time_utc: str, valid_bj: str) -> int:
    """由北京时有效时间反推预报时效（小时）。"""
    init_dt = datetime.strptime(init_time_utc, "%Y%m%d%H")
    valid_utc = datetime.strptime(valid_bj, "%Y-%m-%d %H:%M") - timedelta(hours=8)
    hours = int((valid_utc - init_dt).total_seconds() // 3600)
    if hours < 0:
        raise ValueError("有效时间早于起报时间")
    return hours
