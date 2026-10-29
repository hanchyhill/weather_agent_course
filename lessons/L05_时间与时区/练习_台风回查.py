"""L5 学员练习：台风查询（T2 北京时 + T4 回查）。

做法：先补全 test_练习_台风回查.py 里的测试用例，再让 Claude Code 实现下面两个函数，
直到测试全部通过：
    uv run pytest "lessons/L05_时间与时区/test_练习_台风回查.py"

可以调用的离线接口：weather_tools.typhoon.request_getyphdata(datetime_bj)
参考答案：weather_tools/typhoon.py 里的 query_typhoon / query_typhoon_with_lookback。
做完之前不要看参考答案。
"""
from weather_tools.typhoon import extract_systems, request_getyphdata  # noqa: F401


def query_typhoon(datetime_str: str, timezone: str = "UTC+8") -> dict:
    """T2：默认北京时；传 'UTC' 时由程序加 8 小时。格式不是 YYYY-MM-DD HH:MM:SS 时报错。"""
    raise NotImplementedError("请让 AI 按需求实现")


def query_typhoon_with_lookback(datetime_str: str, timezone: str = "UTC+8") -> dict:
    """T4：目标时次没有台风时，每 3 小时往前查，最多 24 小时（共 9 次）。

    - 命中：返回接口原文，并加上 query_metadata（实际时次、回查小时数、是否回查、每次尝试记录）
    - 24 小时都没有：返回 status='not_applicable'，message 里写明“不应请求依赖 tsid 的诊断图或路径图”
    - 返回结构不认识（extract_systems 返回 None）：原样返回
    """
    raise NotImplementedError("请让 AI 按需求实现")
