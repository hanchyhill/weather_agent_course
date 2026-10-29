"""L12 真实天气接口：基于 agent_dev 的地点天气查询。"""
import json
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv
from langchain_core.tools import tool

from common.paths import COURSE_ROOT
from common.weather_http import get as weather_get

load_dotenv(COURSE_ROOT / ".env", override=True)
BASE_URL = os.getenv("BASE_URL_WEATHER_API", "").strip().rstrip("/")
if not BASE_URL:
    raise RuntimeError("请在课程 .env 设置 BASE_URL_WEATHER_API，再重新运行本单元格。")
BJ = ZoneInfo("Asia/Shanghai")
FMT = "%Y-%m-%d %H:%M:%S"

def request_weather(path, params=None):
    """请求真实服务；网络、HTTP 和接口错误都明确返回给调用方。"""
    try:
        response = weather_get(BASE_URL + path, params=params, timeout=20)
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        return {"status": "error", "message": f"天气服务请求失败：{type(exc).__name__}: {exc}"}
    if not isinstance(payload, dict) or "data" not in payload:
        return {"status": "error", "message": "服务响应缺少 data 字段", "response": payload}
    if "status" in payload and payload["status"] != 1:
        return {"status": "error", "message": "天气服务返回失败状态", "response": payload}
    return {"status": "ok", "data": payload["data"]}

def as_json(value):
    return json.dumps(value, ensure_ascii=False, default=str)

def validate_window(start_time, end_time):
    start = datetime.strptime(start_time, FMT)
    end = datetime.strptime(end_time, FMT)
    if start > end:
        raise ValueError("开始时间不能晚于结束时间")
    return start, end

def latest_cycle(now):
    """按原项目规则选择北京时间 08 时或 20 时起报。"""
    cycle = now.replace(hour=20 if now.hour >= 20 or now.hour < 8 else 8,
                        minute=0, second=0, microsecond=0)
    return cycle - timedelta(days=1) if now.hour < 8 else cycle



@tool
def get_station_history(address: str, start_time: str, end_time: str) -> str:
    """按地点名称查询真实历史实况，时间为北京时 YYYY-MM-DD HH:MM:SS。
    参数 address 为地点名称；start_time、end_time 为查询开始和结束时间。"""
    try:
        validate_window(start_time, end_time)
    except ValueError as exc:
        return as_json({"status": "error", "message": str(exc)})
    return as_json(request_weather("/llmserver/getrealdata",
                   {"address": address, "stime": start_time, "etime": end_time, "type": 1}))

@tool
def get_forecast(address: str, start_time: str, end_time: str) -> str:
    """按地点名称查询真实天气预报，时间为北京时 YYYY-MM-DD HH:MM:SS。
    起报时间按当前北京时选择最近的 08 或 20 时；只查询起报时刻之后的时间。"""
    try:
        start, end = validate_window(start_time, end_time)
    except ValueError as exc:
        return as_json({"status": "error", "message": str(exc)})
    cycle = latest_cycle(datetime.now(BJ)).replace(tzinfo=None)
    effective_start = max(start, cycle + timedelta(hours=1))
    if effective_start > end:
        return as_json({"status": "no_data", "message": "查询时段不在当前起报时次之后", "cycle_bj": cycle.strftime(FMT)})
    result = request_weather("/llmserver/getforedata", {"address": address,
        "starttime": cycle.strftime(FMT), "stime": effective_start.strftime(FMT),
        "etime": end_time, "type": 1})
    result["cycle_bj"] = cycle.strftime(FMT)
    result["actual_start_bj"] = effective_start.strftime(FMT)
    return as_json(result)

@tool
def get_current_beijing_time() -> str:
    """获取真实当前北京时间，处理昨天、今天和明天之前先调用。"""
    return datetime.now(BJ).strftime(FMT)
