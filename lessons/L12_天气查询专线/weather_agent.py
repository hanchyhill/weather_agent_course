"""L12 天气查询专线：五步用到的工具、提示词和检查函数。

W1  地名 → 经纬度            geocode_place
W2  经纬度 → 实况站点历史     get_station_history（世界时）
W3  经纬度 → 预报            get_forecast（世界时）
W4  提示词：问“今天”要同时查实况和预报
W5  提示词 / 工具：用户说北京时，接口是世界时
      方案 A 改提示词：把换算规则写进去（模型心算，不可靠）
      方案 B 改工具：  *_bj 版本直接收北京时，换算和补 time_bj 由程序完成（推荐）
"""
import json
from datetime import datetime, timedelta

from langchain_core.tools import tool

from weather_tools import weather as wx

# ------------------------------------------------------------------ W1
@tool
def geocode_place(place: str) -> str:
    """根据地名查询经纬度，返回 JSON。查询任何地点的天气前必须先调用，不要自己猜经纬度。

    参数 place：地名，如“广州天河区”“深圳福田区”。
    返回 status：ok（唯一结果，取 candidates[0] 的 lon、lat）、ambiguous（有多个同名地点，
    此时不要自己挑，向用户确认是哪个省市）、not_found（没有这个地点，如实告知用户）。
    """
    return json.dumps(wx.geocode(place), ensure_ascii=False)


# ------------------------------------------------------------------ W2
def _dump(result: dict) -> str:
    return json.dumps(result, ensure_ascii=False)


@tool
def get_station_history(lon: float, lat: float, start_time: str, end_time: str) -> str:
    """查询某经纬度附近最近实况站点的逐小时历史观测（已经发生的天气），返回 JSON。

    参数：
    - lon、lat：经度、纬度，来自 geocode_place。
    - start_time、end_time：起止时间（含两端），世界时（UTC），格式 YYYY-MM-DD HH:MM:SS。
    返回 summary 为区间统计（气温最低/最高 ℃、累计降水 mm、最大风速和阵风 m/s、最小能见度 km），
    rows 为逐小时记录。status 为 no_data 时说明该时间段没有实况（例如时间在未来），
    不要编造数据。
    """
    try:
        return _dump(wx.query_station_history(lon, lat, start_time, end_time))
    except ValueError as exc:
        return f"参数错误：{exc}"


# ------------------------------------------------------------------ W3
@tool
def get_forecast(lon: float, lat: float, start_time: str, end_time: str) -> str:
    """查询某经纬度附近的逐小时天气预报（还没发生的天气），返回 JSON。

    参数：
    - lon、lat：经度、纬度，来自 geocode_place。
    - start_time、end_time：起止时间（含两端），世界时（UTC），格式 YYYY-MM-DD HH:MM:SS。
    返回结构和 get_station_history 相同。预报只覆盖起报时间之后的时段；
    status 为 no_data 时说明时间段不在预报范围内。
    """
    try:
        return _dump(wx.query_forecast(lon, lat, start_time, end_time))
    except ValueError as exc:
        return f"参数错误：{exc}"


# ------------------------------------------------------------------ W5 方案 B
@tool
def get_station_history_bj(lon: float, lat: float, start_time: str, end_time: str) -> str:
    """查询某经纬度附近最近实况站点的逐小时历史观测（已经发生的天气），返回 JSON。

    参数：
    - lon、lat：经度、纬度，来自 geocode_place。
    - start_time、end_time：起止时间（含两端），**北京时**，格式 YYYY-MM-DD HH:MM:SS。
      用户说的“昨天”就是昨天 00:00:00 ~ 23:00:00，直接传，不要自己换算时区。
    返回 summary 为区间统计，rows 为逐小时记录，每条同时有 datetime（世界时）和 time_bj（北京时），
    回答时只用 time_bj。status 为 no_data 表示该时间段没有实况，不要编造数据。
    """
    try:
        s, e = wx.bj_range_to_utc(start_time, end_time)
        return _dump(wx.add_bj_time(wx.query_station_history(lon, lat, s, e)))
    except ValueError as exc:
        return f"参数错误：{exc}"


@tool
def get_forecast_bj(lon: float, lat: float, start_time: str, end_time: str) -> str:
    """查询某经纬度附近的逐小时天气预报（还没发生的天气），返回 JSON。

    参数：
    - lon、lat：经度、纬度，来自 geocode_place。
    - start_time、end_time：起止时间（含两端），**北京时**，格式 YYYY-MM-DD HH:MM:SS，直接传，不要自己换算时区。
    返回结构和 get_station_history_bj 相同（rows 里有 time_bj）。
    """
    try:
        s, e = wx.bj_range_to_utc(start_time, end_time)
        return _dump(wx.add_bj_time(wx.query_forecast(lon, lat, s, e)))
    except ValueError as exc:
        return f"参数错误：{exc}"


# ------------------------------------------------------------------ 提示词
SYSTEM_W1 = """你是广东省气象台的天气查询助手。
回答天气问题的步骤：先用 geocode_place 查地点经纬度，再用天气工具取数据，最后用通俗的中文总结。
只根据工具返回的数据回答，工具没有数据就如实说明。"""

# W4：加“今天”规则
SYSTEM_W4 = SYSTEM_W1 + """

选工具的规则（按时间判断，不要凭感觉）：
- 整个时间段都在“现在”之前：只用 get_station_history。
- 整个时间段都在“现在”之后：只用 get_forecast。
- 时间段跨过“现在”（典型的是“今天”）：必须两个都查。get_station_history 查从 00 时到现在，
  get_forecast 查从现在到 23 时。回答时分成“截至目前的实况”和“接下来的预报”两段，不要把两者混在一起。
- 现在是几点，先调用 get_beijing_time 确认。"""

# W5 方案 A：只改提示词，把换算规则写进去
SYSTEM_W5_PROMPT = SYSTEM_W4 + """

时间换算规则：用户说的时间都是北京时，而 get_station_history、get_forecast 只接受世界时（UTC），
传参前必须把北京时减 8 小时。例如北京时 2026-08-10 00:00:00 要传 2026-08-09 16:00:00。
工具返回的 datetime 是世界时，回答时要加 8 小时换回北京时再告诉用户。"""

# W5 方案 B：工具负责换算，提示词只要求“都用北京时”
SYSTEM_W5_TOOL = SYSTEM_W1 + """

选工具的规则（按时间判断，不要凭感觉）：
- 整个时间段都在“现在”之前：只用 get_station_history_bj。
- 整个时间段都在“现在”之后：只用 get_forecast_bj。
- 时间段跨过“现在”（如“今天”）：两个都查，分成“截至目前的实况”和“接下来的预报”两段回答。
- 现在是几点，先调用 get_beijing_time 确认。
所有时间一律使用北京时，不需要做时区换算。"""


# ------------------------------------------------------------------ 检查函数
def expected_windows(now_bj: datetime) -> dict:
    """以 now_bj 为“现在”，给出昨天/今天/明天各应当查询的世界时窗口（整点）。

    history：实况窗口（截止到“现在”所在小时的上一整点，因为实况有延迟，这里放宽到现在所在小时）。
    forecast：预报窗口。没有的为 None。
    """
    d0 = now_bj.replace(hour=0, minute=0, second=0, microsecond=0)

    def utc(t: datetime) -> str:
        return (t - timedelta(hours=8)).strftime(wx.FMT)

    return {
        "yesterday": {"history": (utc(d0 - timedelta(days=1)), utc(d0 - timedelta(hours=1))), "forecast": None},
        "today": {"history": (utc(d0), utc(now_bj.replace(minute=0, second=0, microsecond=0))),
                  "forecast": (utc(now_bj.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)),
                               utc(d0 + timedelta(hours=23)))},
        "tomorrow": {"history": None, "forecast": (utc(d0 + timedelta(days=1)), utc(d0 + timedelta(hours=47)))},
    }


def check_calls(calls: list[dict], expect: dict, *, hist_tool: str, fore_tool: str,
                bj_args: bool = False, tol_hours: int = 1) -> list[str]:
    """核对模型的工具调用：该调的工具调了没有、不该调的有没有调、时间窗口对不对。

    calls 来自 common.trace.tool_calls(result)。bj_args=True 表示工具参数是北京时（W5 方案 B）。
    返回问题列表，空表示通过。
    """
    problems = []
    shift = timedelta(hours=8) if bj_args else timedelta(0)

    def hours_off(got: str, want: str) -> float:
        g = datetime.strptime(got, wx.FMT) - shift
        return abs((g - datetime.strptime(want, wx.FMT)).total_seconds()) / 3600

    for key, tool_name in (("history", hist_tool), ("forecast", fore_tool)):
        want = expect[key]
        mine = [c for c in calls if c["name"] == tool_name]
        if want is None:
            if mine:
                problems.append(f"不该调用 {tool_name}")
            continue
        if not mine:
            problems.append(f"漏调了 {tool_name}")
            continue
        try:
            ok = any(hours_off(c["args"]["start_time"], want[0]) <= tol_hours
                     and hours_off(c["args"]["end_time"], want[1]) <= tol_hours for c in mine)
        except (KeyError, ValueError):
            ok = False
        if not ok:
            shown = [(c["args"].get("start_time"), c["args"].get("end_time")) for c in mine]
            problems.append(f"{tool_name} 的时间窗口不对：传入 {shown}，应约为 "
                            f"{(datetime.strptime(want[0], wx.FMT) + shift).strftime(wx.FMT)} ~ "
                            f"{(datetime.strptime(want[1], wx.FMT) + shift).strftime(wx.FMT)}")
    if not any(c["name"] == "geocode_place" for c in calls):
        problems.append("没有先查经纬度")
    return problems
