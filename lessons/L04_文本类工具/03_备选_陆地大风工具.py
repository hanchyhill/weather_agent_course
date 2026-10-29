"""备选练习：陆地大风统计工具（改写自 agent_dev/src/tools/ToolDecision.py 的 windLand）。

原工具调用内网接口（陆地大风），把返回的 JSON 拼成中文句子，不调用模型。
这里用一份教学构造的离线数据演示“JSON → 中文播报句”的写法。

学员任务：让 Claude Code 按下面的需求补全 build_sentence，并让测试通过：
    uv run pytest lessons/L04_文本类工具
"""
from datetime import datetime, timedelta

# 教学构造的接口返回（格式参照 agent_dev windLand 读取的字段）
SAMPLE = {
    "status": 1,
    "data": {
        "avg": {"city": "湛江", "name": "徐闻", "value": 15.2},
        "max": {"city": "阳江", "name": "海陵岛", "value": 24.6},
    },
}


def normalize_range(starttime: str, endtime: str) -> tuple[str, str]:
    """开始和结束时间相同时，开始时间往前推 3 小时（agent_dev 的做法）。"""
    fmt = "%Y-%m-%d %H:%M:%S"
    s, e = datetime.strptime(starttime, fmt), datetime.strptime(endtime, fmt)
    if s == e:
        s -= timedelta(hours=3)
    return s.strftime(fmt), e.strftime(fmt)


def build_sentence(payload: dict) -> str:
    """把接口返回拼成播报句。

    期望输出：
    我省陆地上湛江市徐闻录得全省最大平均风15.2m/s，阳江市海陵岛录得全省最大阵风24.6m/s。
    """
    if payload.get("status") != 1:
        return "大风数据查询失败。"
    avg, mx = payload["data"]["avg"], payload["data"]["max"]
    return (f"我省陆地上{avg['city']}市{avg['name']}录得全省最大平均风{avg['value']}m/s，"
            f"{mx['city']}市{mx['name']}录得全省最大阵风{mx['value']}m/s。")


if __name__ == "__main__":
    print(normalize_range("2026-08-11 08:00:00", "2026-08-11 08:00:00"))
    print(build_sentence(SAMPLE))
