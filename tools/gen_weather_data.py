"""讲师用：生成 L12 天气专线的离线数据（教学构造，不是真实观测）。

用法：uv run python tools/gen_weather_data.py

生成 data/weather/ 下三个文件：
- gazetteer.json   地名库（地点 → 经纬度）
- station_real.json 实况站点逐小时记录，时间为世界时（UTC）
- forecast.json     预报格点逐小时数据，时间为世界时（UTC），起报 2026-08-11 00 UTC（北京时 08 时）

字段名参照 agent_dev 的天气接口：t2mm 气温(℃)、rain 小时降水(mm)、wind_vel 风速(m/s)、
wind_dir 风向(度)、gust 阵风(m/s)、visi 能见度(km)。
天气过程是人为设定的，用来检验学员能否取对时间段：
- 昨天(8/10)  午后 15-17 时（北京时）雷阵雨
- 今天(8/11)  上午晴，傍晚 17-18 时有阵雨
- 明天(8/12)  午后 14-18 时中到大雨
"""
import json
import math
import random
from datetime import datetime, timedelta
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "data" / "weather"
FMT = "%Y-%m-%d %H:%M:%S"
DATA_START = datetime(2026, 8, 9, 0)      # UTC
DATA_END = datetime(2026, 8, 13, 0)       # UTC
REAL_END = datetime(2026, 8, 11, 0)       # 实况最后一条：UTC 8/11 00 = 北京时 08 时
FORECAST_START = datetime(2026, 8, 11, 1)  # 预报第一条

# 北京日期 -> {北京时小时: 小时降水 mm}
RAIN_BJ = {
    "2026-08-10": {15: 4.2, 16: 12.6, 17: 3.1},
    "2026-08-11": {17: 6.5, 18: 2.0},
    "2026-08-12": {14: 2.0, 15: 8.5, 16: 20.3, 17: 11.2, 18: 3.4},
}

POINTS = [
    # id, 名称, 经度, 纬度, 气温偏差, 降水系数
    ("G0001", "广州天河（教学站）", 113.36, 23.12, 0.0, 1.0),
    ("G0002", "广州越秀（教学站）", 113.27, 23.13, 0.4, 0.7),
    ("G0003", "深圳福田（教学站）", 114.05, 22.53, 0.2, 0.5),
]

GAZETTEER = [
    {"name": "天河区", "province": "广东省", "city": "广州市", "level": "区县",
     "lon": 113.361, "lat": 23.125, "aliases": ["广州天河区", "天河区", "天河"]},
    {"name": "天河城", "province": "广东省", "city": "广州市", "level": "兴趣点",
     "lon": 113.331, "lat": 23.133, "aliases": ["天河城", "广州天河城"]},
    {"name": "越秀区", "province": "广东省", "city": "广州市", "level": "区县",
     "lon": 113.267, "lat": 23.129, "aliases": ["广州越秀区", "越秀区", "越秀"]},
    {"name": "广州市", "province": "广东省", "city": "广州市", "level": "地级市",
     "lon": 113.264, "lat": 23.129, "aliases": ["广州", "广州市"]},
    {"name": "福田区", "province": "广东省", "city": "深圳市", "level": "区县",
     "lon": 114.055, "lat": 22.521, "aliases": ["深圳福田区", "福田区", "福田"]},
    {"name": "朝阳区", "province": "北京市", "city": "北京市", "level": "区县",
     "lon": 116.443, "lat": 39.921, "aliases": ["北京朝阳区", "朝阳区"]},
    {"name": "朝阳区", "province": "吉林省", "city": "长春市", "level": "区县",
     "lon": 125.288, "lat": 43.834, "aliases": ["长春朝阳区", "朝阳区"]},
]


def _hours(a: datetime, b: datetime):
    t = a
    while t <= b:
        yield t
        t += timedelta(hours=1)


def _row(t_utc: datetime, dt_off: float, rain_k: float, rng: random.Random) -> dict:
    bj = t_utc + timedelta(hours=8)
    base = 29 + 5 * math.cos(2 * math.pi * (bj.hour - 15) / 24) + dt_off
    rain = round(RAIN_BJ.get(bj.strftime("%Y-%m-%d"), {}).get(bj.hour, 0.0) * rain_k, 1)
    temp = base - (3.5 if rain >= 1 else 0) + rng.uniform(-0.3, 0.3)
    wind = 2.2 + rng.uniform(-0.6, 0.8) + (3.5 if rain >= 1 else 0)
    gust = wind * 1.6 + (4.0 if rain >= 5 else 0)
    return {
        "datetime": t_utc.strftime(FMT),
        "t2mm": round(temp, 1),
        "rain": rain,
        "wind_vel": round(wind, 1),
        "wind_dir": int(165 + rng.uniform(-25, 25)) % 360,
        "gust": round(gust, 1),
        "visi": round(20 - min(rain, 15) * 0.9 + rng.uniform(-0.5, 0.5), 1),
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    stations, grids = [], []
    for i, (sid, name, lon, lat, dt_off, rain_k) in enumerate(POINTS):
        rng = random.Random(100 + i)
        rows = [_row(t, dt_off, rain_k, rng) for t in _hours(DATA_START, DATA_END)]
        real = [r for r in rows if r["datetime"] <= REAL_END.strftime(FMT)]
        fore = [r for r in rows if r["datetime"] >= FORECAST_START.strftime(FMT)]
        stations.append({"station": sid, "name": name, "lon": lon, "lat": lat, "data": real})
        grids.append({"grid": f"F{sid[1:]}", "name": name.replace("教学站", "教学格点"),
                      "lon": lon, "lat": lat, "data": fore})
    (OUT / "station_real.json").write_text(json.dumps(
        {"_说明": "教学构造数据，时间为世界时(UTC)。实况截止 2026-08-11 00:00 UTC（北京时 08 时）。",
         "stations": stations}, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT / "forecast.json").write_text(json.dumps(
        {"_说明": "教学构造数据，时间为世界时(UTC)。起报 2026-08-11 00:00 UTC（北京时 08 时）。",
         "starttime": "2026-08-11 00:00:00", "grids": grids}, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT / "gazetteer.json").write_text(json.dumps(
        {"_说明": "教学用迷你地名库，经纬度为区域中心的近似值。", "places": GAZETTEER},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print("已生成", OUT)


if __name__ == "__main__":
    main()
