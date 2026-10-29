"""台风报告验收清单（T8）：用程序检查智能体的运行轨迹和报告。

清单分两类：
- 轨迹检查：调用顺序、tsid 来源、无台风时不取图。程序能判断。
- 报告检查：必备章节、每个台风都出现。程序能粗查，内容质量要人看（L10 用评分表）。
"""
import json
import re

from common.trace import final_text, tool_calls

REQUIRED_SECTIONS = ["台风概况", "路径", "影响", "结论"]


def _query_result(result: dict) -> dict | None:
    from langchain_core.messages import ToolMessage
    for m in result["messages"]:
        if isinstance(m, ToolMessage) and m.name == "get_typhoon_data_by_datetime":
            try:
                return json.loads(m.content)
            except (TypeError, json.JSONDecodeError):
                return None
    return None


def check(result: dict) -> list[tuple[str, bool, str]]:
    calls = tool_calls(result)
    names = [c["name"] for c in calls]
    report = final_text(result)
    q = _query_result(result)
    items: list[tuple[str, bool, str]] = []

    items.append(("先查询台风", "get_typhoon_data_by_datetime" in names, ""))

    no_tc = bool(q) and q.get("status") == "not_applicable"
    track_calls = [c for c in calls if c["name"] == "interpret_tc_track_forecast_chart"]
    if no_tc:
        items.append(("无台风时不取路径图", not track_calls, f"调用了 {len(track_calls)} 次"))
        items.append(("报告说明无台风", bool(re.search(r"没有|无活动台风|无台风", report)), ""))
        return items

    tsids = [str(t) for t in (q or {}).get("tsid", [])]
    used = [str(c["args"].get("tsid")) for c in track_calls]
    items.append(("tsid 来自查询结果", all(u in tsids for u in used), f"查询 {tsids}，使用 {used}"))
    if track_calls:
        first_query = names.index("get_typhoon_data_by_datetime")
        first_track = names.index("interpret_tc_track_forecast_chart")
        items.append(("先查台风再取路径图", first_query < first_track, ""))

    # “2026年第13号台风白海豚” → “白海豚”（等级词可能是台风、强台风、热带风暴等）
    names_in_q = [re.sub(r"^\d{4}年第\d+号(超强台风|强台风|台风|强热带风暴|热带风暴|热带低压)?", "",
                         d.get("台风信息", "")) for d in (q or {}).get("data", [])]
    missing = [n for n in names_in_q if n and n not in report]
    items.append(("每个台风都写进报告", not missing, f"缺少 {missing}" if missing else ""))

    lacking = [s for s in REQUIRED_SECTIONS if s not in report]
    items.append(("必备章节齐全", not lacking, f"缺少 {lacking}" if lacking else ""))
    return items


def print_check(result: dict) -> None:
    for name, ok, detail in check(result):
        print(f"{'✓' if ok else '✗'} {name} {detail}")
