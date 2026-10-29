"""台风工具（离线版），对应台风专线 T1～T6 的参考实现。

规则来自 huishang_demo/src/tools/typhoon_tools.py：
- get_typhoon_data_by_datetime：北京时查询，空结果每 3 小时回查，最多 24 小时
- _extract_typhoon_systems：只认识明确的系统列表
- interpret_tc_track_forecast_chart：路径图时次与候选回退
- _resolve_tc_diagnostic_tsid：业务编号转诊断图编号

离线数据：data/typhoon_api/getyphdata.json（来自 huishang_demo 真实运行日志）。
"""
import base64
import json
import os
from datetime import datetime, timedelta
from functools import lru_cache
from urllib.parse import quote

from weather_tools.timeutil import Tz, convert_tz
from common.paths import DATA_DIR

LOOKBACK_HOURS = 24
CYCLE_HOURS = 3
TRACK_CYCLE_HOURS_BJ = (2, 8, 14, 20)

# 取数地址不写明文：优先读环境变量 TYPHOON_API_URL（讲师可指向自己的代理），
# 未设置时用下面这段编码后的内置地址。
_ENDPOINT = "aHR0cDovL3RtcC5nZG1vLm9yZzo4MS9sbG1zZXJ2ZXIvZ2V0eXBoZGF0YT9kYXRldGltZT17ZGF0ZXRpbWVfYmp9"

# 诊断图编号对照。真实系统通过 getxxzx 接口查询。
# 554→803 来自 huishang_demo/台风图像.md 的示例；其余为教学构造的占位编号，不是真实编号。
DIAGNOSTIC_TSID = {"554": "803", "547": "9547", "550": "9550"}


@lru_cache(maxsize=1)
def _offline_db() -> dict:
    return json.loads((DATA_DIR / "typhoon_api" / "getyphdata.json").read_text(encoding="utf-8"))


def data_endpoint(datetime_bj: str) -> str:
    """拼出取数地址（接口参数只认北京时）。地址不在讲义里明文出现。

    用 TYPHOON_API_URL 环境变量可覆盖，留空则用课程内置地址。
    """
    tmpl = os.getenv("TYPHOON_API_URL", "").strip() or base64.b64decode(_ENDPOINT).decode()
    return tmpl.format(datetime_bj=quote(datetime_bj, safe=""))


def request_getyphdata(datetime_bj: str) -> dict:
    """离线模拟 getyphdata 接口：按北京时 'YYYY-MM-DD HH:MM:SS' 取数。

    离线库里没有的时次，按“该时次无台风”返回空列表。
    """
    datetime.strptime(datetime_bj, "%Y-%m-%d %H:%M:%S")  # 格式检查
    return _offline_db().get(datetime_bj, {"status": 1, "tsid": [], "datetime": [], "data": []})


def extract_systems(payload: object) -> list | None:
    """取出台风系统列表；结构不认识时返回 None（不乱下结论）。"""
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return None
    data = payload.get("data")
    if isinstance(data, list):
        return data
    return None


def query_typhoon_utc(datetime_utc: str) -> dict:
    """T1：只接受世界时的查询（还原的早期版本）。内部转北京时请求离线接口。"""
    bj = convert_tz(datetime_utc, "%Y-%m-%d %H:%M:%S", "UTC", "UTC+8")
    return request_getyphdata(bj)


def query_typhoon(datetime_str: str, timezone: Tz = "UTC+8") -> dict:
    """T2：默认北京时；传 UTC 时由程序换算。不做回查。"""
    bj = datetime_str if timezone == "UTC+8" else convert_tz(
        datetime_str, "%Y-%m-%d %H:%M:%S", "UTC", "UTC+8")
    datetime.strptime(bj, "%Y-%m-%d %H:%M:%S")
    return request_getyphdata(bj)


def query_typhoon_with_lookback(datetime_str: str, timezone: Tz = "UTC+8") -> dict:
    """T4：目标时次为空时每 3 小时向前回查，最多 24 小时（共 9 次）。"""
    bj = datetime_str if timezone == "UTC+8" else convert_tz(
        datetime_str, "%Y-%m-%d %H:%M:%S", "UTC", "UTC+8")
    requested = datetime.strptime(bj, "%Y-%m-%d %H:%M:%S")
    attempts = []
    for offset in range(0, LOOKBACK_HOURS + 1, CYCLE_HOURS):
        cand = (requested - timedelta(hours=offset)).strftime("%Y-%m-%d %H:%M:%S")
        payload = request_getyphdata(cand)
        systems = extract_systems(payload)
        attempts.append({
            "datetime_bj": cand,
            "offset_hours": offset,
            "systems_count": None if systems is None else len(systems),
        })
        if systems is None:
            # 结构不认识：原样返回，交给人判断
            return payload
        if systems:
            result = dict(payload)
            result["query_metadata"] = {
                "requested_datetime_bj": bj,
                "actual_datetime_bj": cand,
                "lookback_hours": offset,
                "fallback_used": offset > 0,
                "query_attempts": attempts,
            }
            return result
    return {
        "status": "not_applicable",
        "requested_datetime_bj": bj,
        "systems": [],
        "query_attempts": attempts,
        "message": f"目标时次及此前{LOOKBACK_HOURS}小时均未获取到活动台风预报信息，"
                   "不应请求依赖 tsid 的诊断图或路径图。",
    }


def summarize(payload: dict) -> str:
    """把接口返回整理成中文简介（T0）。"""
    if payload.get("status") == "not_applicable":
        return payload["message"]
    systems = extract_systems(payload)
    if systems is None:
        return f"接口返回的结构无法识别：{json.dumps(payload, ensure_ascii=False)[:200]}"
    if not systems:
        return "该时次没有活动台风。"
    lines = []
    for tsid, dt, item in zip(payload.get("tsid", []), payload.get("datetime", []), systems):
        track = item.get("路径信息", [])
        now = track[0] if track else {}
        lines.append(
            f"{item.get('台风信息')}（tsid={tsid}，资料时次 {dt}）：预报发布于 {now.get('预报时间')}，"
            f"{now.get('预报时效')}位于 {now.get('纬度')}°N、{now.get('经度')}°E，"
            f"中心风力 {now.get('中心风力')}，气压 {now.get('中心气压')}，"
            f"向 {now.get('移动方向')} 移动，{now.get('移动速度')}。"
        )
    return "\n".join(lines)


def track_candidates(forecast_time_bj: str, max_candidates: int = 3) -> list[str]:
    """T5：路径图时次候选。先用请求时次，再试最近的下一个时次，再试上一个时次。

    北京时小时必须是 02/08/14/20。
    """
    dt = datetime.strptime(forecast_time_bj, "%Y-%m-%d %H:%M:%S")
    cands = [dt]
    h = dt.hour
    forward = sorted((c - h) % 24 for c in TRACK_CYCLE_HOURS_BJ if (c - h) % 24)
    backward = sorted((h - c) % 24 for c in TRACK_CYCLE_HOURS_BJ if (h - c) % 24)
    for off in ([forward[0]] if forward else [24]) + ([-backward[0]] if backward else []):
        c = dt + timedelta(hours=off)
        if c not in cands:
            cands.append(c)
    return [c.strftime("%Y-%m-%d %H:%M:%S") for c in cands[:max_candidates]]


def track_image_path(tsid: str, forecast_time_bj: str):
    """T5：离线路径图。图片按 UTC YYYYMMDDHH 命名（与 mllm_test 一致）。

    返回 (路径, 实际使用的北京时, 是否回退)；都找不到时返回 (None, None, False)。
    """
    for i, cand in enumerate(track_candidates(forecast_time_bj)):
        utc = convert_tz(cand, "%Y-%m-%d %H:%M:%S", "UTC+8", "UTC")
        key = datetime.strptime(utc, "%Y-%m-%d %H:%M:%S").strftime("%Y%m%d%H")
        p = DATA_DIR / "typhoon_track" / "images" / f"{tsid}_{key}.png"
        if p.exists():
            return p, cand, i > 0
    return None, None, False


def resolve_diagnostic_tsid(business_tsid: str) -> str:
    """T6：业务编号 → 诊断图编号。找不到时给出明确的错误原因。"""
    if not business_tsid.isdigit():
        raise ValueError(f"tsid 应为数字字符串，实际: {business_tsid}")
    try:
        return DIAGNOSTIC_TSID[business_tsid]
    except KeyError:
        raise LookupError(
            f"业务编号 {business_tsid} 没有对应的诊断图编号。"
            "诊断图服务与台风动态接口使用两套编号，需先查询编号转换接口。"
        ) from None
