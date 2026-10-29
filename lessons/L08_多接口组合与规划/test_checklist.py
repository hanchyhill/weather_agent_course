"""用假模型跑台风智能体，检查验收清单本身是否判得对。"""
import os

os.environ["COURSE_FAKE_LLM"] = "1"

from common.fake import call, scripted  # noqa: E402
from lessons_import import load_lesson_module  # noqa: E402

ta = load_lesson_module("L08_多接口组合与规划", "typhoon_agent")
ck = load_lesson_module("L08_多接口组合与规划", "checklist")

GOOD = "# 标题\n## 台风概况\n白海豚……灿鸿……\n## 路径预报\n……\n## 对广东和南海的影响\n……\n## 结论\n……"


def _run(*turns):
    agent = ta.build_typhoon_agent(scripted(*turns))
    return agent.invoke({"messages": [{"role": "user", "content": "分析台风"}]})


def _items(result):
    return {name: ok for name, ok, _ in ck.check(result)}


def test_two_typhoons_good_report_passes():
    r = _run(
        call("get_typhoon_data_by_datetime", datetime="2026-08-11 08:00:00"),
        call("interpret_tc_track_forecast_chart", "c2", tsid="547", forecast_time="2026-08-11 08:00:00"),
        GOOD,
    )
    assert all(_items(r).values()), ck.check(r)


def test_missing_typhoon_and_fake_tsid_are_caught():
    r = _run(
        call("get_typhoon_data_by_datetime", datetime="2026-08-11 08:00:00"),
        call("interpret_tc_track_forecast_chart", "c2", tsid="123", forecast_time="2026-08-11 08:00:00"),
        "# 标题\n## 台风概况\n白海豚……\n## 路径\n## 影响\n## 结论",
    )
    items = _items(r)
    assert items["tsid 来自查询结果"] is False
    assert items["每个台风都写进报告"] is False


def test_no_typhoon_branch():
    r = _run(
        call("get_typhoon_data_by_datetime", datetime="2026-07-23 08:00:00"),
        "过去 24 小时没有活动台风。",
    )
    items = _items(r)
    assert items["无台风时不取路径图"] and items["报告说明无台风"]
