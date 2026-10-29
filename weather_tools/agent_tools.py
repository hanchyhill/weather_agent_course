"""交给智能体使用的 @tool 版本。

docstring 就是写给模型看的“使用说明”：什么时候用、参数格式、返回什么。
L8 以后的台风智能体直接导入这里的工具。
"""
import json

from langchain_core.tools import tool

from common.clock import now_bj
from common.paths import DATA_DIR
from weather_tools import typhoon
from weather_tools.vision import interpret_image


@tool
def get_beijing_time() -> str:
    """获取当前北京时间，格式 YYYY-MM-DD HH:MM。回答与“现在”“今天”“过去24小时”有关的问题前先调用。"""
    return now_bj().strftime("%Y-%m-%d %H:%M")


@tool
def get_typhoon_data_by_datetime(datetime: str, timezone: str = "UTC+8") -> str:
    """按时间查询西北太平洋活动台风，返回 JSON。

    参数：
    - datetime：时间字符串，格式 YYYY-MM-DD HH:MM:SS。
    - timezone：datetime 的时区，'UTC+8'（默认，北京时）或 'UTC'（世界时）。时区换算由工具完成，不要自己加减 8 小时。

    资料时次为北京时 02/05/08/11/14/17/20/23。目标时次没有资料时，工具每 3 小时向前回查，最多 24 小时。
    返回 status 为 not_applicable 表示过去 24 小时没有活动台风，此时不要再调用依赖 tsid 的工具。
    返回多个台风时，每个台风都要给出结论。
    """
    result = typhoon.query_typhoon_with_lookback(datetime, timezone)  # type: ignore[arg-type]
    return json.dumps(result, ensure_ascii=False, indent=1)


@tool
def interpret_tc_track_forecast_chart(tsid: str, forecast_time: str, prompt: str = "") -> str:
    """解读台风路径预报图（广州 BCGZ 路径图）。

    必须先调用 get_typhoon_data_by_datetime 拿到 tsid，再调用本工具，不要自己编 tsid。
    参数：
    - tsid：台风业务编号（数字字符串），来自台风查询结果的 tsid 字段。
    - forecast_time：北京时 YYYY-MM-DD HH:MM:SS，小时必须是 02/08/14/20。没有图时工具会尝试相邻时次。
    - prompt：判读要求，可留空使用默认要求。
    """
    path, used, fallback = typhoon.track_image_path(tsid, forecast_time)
    if path is None:
        return (f"未找到 tsid={tsid} 在 {forecast_time} 及相邻时次的路径图："
                f"{typhoon.track_candidates(forecast_time)}")
    prompt = prompt or ("请解读台风路径预报图：1) 当前位置与强度；2) 未来路径走向与转向点；"
                        "3) 强度变化阶段；4) 可能登陆或近海的时段与地点。"
                        "输出：结论一句话；证据要点3-6条。只写图上能看到的内容。")
    meta = f"产品：台风路径预报图（BCGZ）\ntsid：{tsid}\n请求时次（北京时）：{forecast_time}\n实际时次（北京时）：{used}"
    if fallback:
        meta += "\n注意：请求时次没有图，已使用相邻时次。"
    return interpret_image(path, prompt, meta=meta)


@tool
def resolve_diagnostic_tsid(business_tsid: str) -> str:
    """把台风业务编号转换为诊断图服务使用的编号。取诊断图前必须先调用。"""
    try:
        return typhoon.resolve_diagnostic_tsid(business_tsid)
    except (LookupError, ValueError) as exc:
        return f"转换失败：{exc}"


@tool
def interpret_tc_env_chart(prompt: str = "") -> str:
    """解读台风环境场多图（离线个例：起报 2026081012 UTC）。

    图1-5 为 700-500hPa 引导气流（时效 24/48/72/96/120 小时），图6-9 为垂直风切变（时效 24/72/96/120 小时）。
    用于分析台风路径成因（引导气流）和强度变化的约束（风切变）。
    """
    path = DATA_DIR / "typhoon_env" / "env_2026081012_steer24-120_shear24-120.jpg"
    prompt = prompt or ("这是 9 张拼图：图1-5 为引导气流，图6-9 为垂直风切变。请说明主导引导气流方向和强弱、"
                        "副高与季风槽位置变化，以及风切变对台风强度的约束。")
    return interpret_image(path, prompt, meta="产品：台风环境场（引导气流+垂直风切变）\n起报：2026081012 UTC（北京时 8 月 10 日 20 时）")


@tool
def interpret_tc_genesis_prob_chart(prompt: str = "") -> str:
    """解读西北太平洋热带气旋活动概率多图（离线个例：起报 202608101200 UTC，时效 72/96/120 小时）。

    图1-3 为 TD 以上强度，图4-6 为 TS 以上强度。
    注意：图示为“活动概率”，包含已有台风的未来活动，不能直接当作新台风生成概率。
    先把高值区和已有台风的位置、路径对照，对不上的标为“归属不明”。
    """
    path = DATA_DIR / "typhoon_env" / "genesis_202608101200_td_ts_72-120h.png"
    prompt = prompt or "请说明各概率高值区的位置、范围和随时间的移动。"
    return interpret_image(path, prompt, meta="产品：热带气旋活动概率（EC 集合）\n起报：202608101200 UTC")
