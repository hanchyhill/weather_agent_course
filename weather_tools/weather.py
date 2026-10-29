"""天气查询离线版：地名 → 经纬度、实况站点历史、格点预报。

接口形态参照 agent_dev 的 ToolGameWeather（getrealdata / getforedata / getWeatherDataReal /
getWeatherDataFore）。离线数据在 data/weather/，由 tools/gen_weather_data.py 生成。

**所有底层函数的时间一律是世界时（UTC）**，和真实接口一致；北京时换算见 L12 的 W5。
"""
import json
import math
from datetime import datetime, timedelta
from functools import lru_cache

from common.paths import DATA_DIR

FMT = "%Y-%m-%d %H:%M:%S"
WEATHER_DIR = DATA_DIR / "weather"
MAX_STATION_KM = 30.0   # 离最近实况站超过这个距离就认为没有可用站点
MAX_GRID_KM = 30.0


@lru_cache(maxsize=None)
def _load(name: str) -> dict:
    return json.loads((WEATHER_DIR / name).read_text(encoding="utf-8"))


def _parse(value: str) -> datetime:
    try:
        return datetime.strptime(value, FMT)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"时间格式错误，应为 YYYY-MM-DD HH:MM:SS，实际: {value!r}") from exc


def distance_km(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """两点间的球面距离（公里）。"""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlon, dlat = math.radians(lon2 - lon1), p2 - p1
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(a))


# ---------------------------------------------------------------- ① 地名 → 经纬度

def geocode(place: str) -> dict:
    """按地名查经纬度。返回 {status, candidates:[...]}。

    status：ok（唯一）、ambiguous（多个同名，需要用户说明）、not_found。
    先按别名全字匹配；匹配不到再按“地名包含”模糊匹配。
    """
    key = (place or "").strip()
    if not key:
        return {"status": "not_found", "query": place, "candidates": []}
    places = _load("gazetteer.json")["places"]
    hits = [p for p in places if key in p["aliases"] or key == p["name"]]
    if not hits:
        hits = [p for p in places if key in p["name"] or p["name"] in key]
    cands = [{"name": p["name"], "province": p["province"], "city": p["city"],
              "level": p["level"], "lon": p["lon"], "lat": p["lat"]} for p in hits]
    status = "not_found" if not cands else ("ok" if len(cands) == 1 else "ambiguous")
    return {"status": status, "query": place, "candidates": cands}


# ---------------------------------------------------------------- 公共：取区间 + 汇总

def _slice(rows: list[dict], start: str, end: str) -> list[dict]:
    s, e = _parse(start), _parse(end)
    if e < s:
        raise ValueError(f"结束时间 {end} 早于开始时间 {start}")
    return [r for r in rows if s <= _parse(r["datetime"]) <= e]


def summarize(rows: list[dict]) -> dict:
    """要素统计：气温范围、累计降水、最大风速和阵风、最小能见度。"""
    if not rows:
        return {}
    rain = [r["rain"] for r in rows]
    return {
        "t2mm_min": min(r["t2mm"] for r in rows),
        "t2mm_max": max(r["t2mm"] for r in rows),
        "rain_total_mm": round(sum(rain), 1),
        "rain_hours": sum(1 for x in rain if x >= 0.1),
        "wind_vel_max": max(r["wind_vel"] for r in rows),
        "gust_max": max(r["gust"] for r in rows),
        "visi_min_km": min(r["visi"] for r in rows),
    }


# ---------------------------------------------------------------- ② 实况站点历史

def query_station_history(lon: float, lat: float, start_utc: str, end_utc: str) -> dict:
    """取离 (lon, lat) 最近的实况站点在 [start_utc, end_utc]（含两端，世界时）的逐小时记录。"""
    stations = _load("station_real.json")["stations"]
    best = min(stations, key=lambda s: distance_km(lon, lat, s["lon"], s["lat"]))
    dist = distance_km(lon, lat, best["lon"], best["lat"])
    if dist > MAX_STATION_KM:
        return {"status": "no_station", "message": f"{MAX_STATION_KM:.0f} 公里内没有实况站点（最近 {dist:.0f} 公里）"}
    rows = _slice(best["data"], start_utc, end_utc)
    last = best["data"][-1]["datetime"]
    if not rows:
        return {"status": "no_data", "station": best["name"], "latest_obs_utc": last,
                "message": f"该时间段没有实况记录；站点最新实况时间（UTC）为 {last}"}
    return {"status": "ok", "station": best["name"], "distance_km": round(dist, 1),
            "time_zone": "UTC", "count": len(rows), "latest_obs_utc": last,
            "summary": summarize(rows), "rows": rows}


# ---------------------------------------------------------------- ③ 预报

def query_forecast(lon: float, lat: float, start_utc: str, end_utc: str) -> dict:
    """取离 (lon, lat) 最近格点在 [start_utc, end_utc]（含两端，世界时）的逐小时预报。"""
    data = _load("forecast.json")
    best = min(data["grids"], key=lambda g: distance_km(lon, lat, g["lon"], g["lat"]))
    dist = distance_km(lon, lat, best["lon"], best["lat"])
    if dist > MAX_GRID_KM:
        return {"status": "no_grid", "message": f"{MAX_GRID_KM:.0f} 公里内没有预报格点（最近 {dist:.0f} 公里）"}
    rows = _slice(best["data"], start_utc, end_utc)
    first, last = best["data"][0]["datetime"], best["data"][-1]["datetime"]
    if not rows:
        return {"status": "no_data", "grid": best["name"], "forecast_range_utc": [first, last],
                "message": f"该时间段没有预报；预报覆盖（UTC）{first} ~ {last}。"
                           "已经过去的时间请用实况工具"}
    return {"status": "ok", "grid": best["name"], "distance_km": round(dist, 1),
            "time_zone": "UTC", "starttime_utc": data["starttime"], "count": len(rows),
            "summary": summarize(rows), "rows": rows}


# ---------------------------------------------------------------- ⑤ 北京时 ↔ 世界时

def bj_range_to_utc(start_bj: str, end_bj: str) -> tuple[str, str]:
    """把北京时区间换成世界时区间（各减 8 小时）。"""
    return (( _parse(start_bj) - timedelta(hours=8)).strftime(FMT),
            (_parse(end_bj) - timedelta(hours=8)).strftime(FMT))


def add_bj_time(result: dict) -> dict:
    """给结果里的每条记录补上北京时字段 time_bj，并把时间区间也标出北京时。"""
    for r in result.get("rows", []):
        r["time_bj"] = (_parse(r["datetime"]) + timedelta(hours=8)).strftime(FMT)
    result["time_zone"] = "UTC（rows 里每条另有 time_bj 为北京时）"
    return result


def day_range_bj(day: str) -> tuple[str, str]:
    """北京时某自然日的起止：00:00:00 ~ 23:00:00（小时数据，最后一个时次是 23 时）。"""
    d = datetime.strptime(day, "%Y-%m-%d")
    return d.strftime(FMT), d.replace(hour=23).strftime(FMT)
