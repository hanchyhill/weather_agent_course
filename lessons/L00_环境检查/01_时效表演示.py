"""演示：列出 ECMWF 某次起报的预报时效表（世界时 / 北京时）。

对应 huishang_demo/demo_forecast_times.py。不调用模型，也不需要网络。
运行：uv run python lessons/L00_环境检查/01_时效表演示.py
"""
from weather_tools.timeutil import ecmwf_init_to_utc, lead_time_table

# 起报时间（世界时，YYYYMMDDHH）。ECMWF 只有 00 和 12 两个起报时次。
INIT_TIME = "2025121612"

init_utc = ecmwf_init_to_utc(INIT_TIME, "UTC")
print(f"起报时间：{init_utc} UTC")
print(f"{'时效(小时)':>10}  {'世界时':<16}  {'北京时':<16}")
for row in lead_time_table(init_utc, max_hours=48):
    print(f"{row['lead_time']:>10}  {row['utc']:<16}  {row['bj']:<16}")
