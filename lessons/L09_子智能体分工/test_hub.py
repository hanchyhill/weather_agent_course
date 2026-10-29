import os

os.environ["COURSE_FAKE_LLM"] = "1"

from langchain_core.messages import ToolMessage  # noqa: E402

from common.fake import call, scripted  # noqa: E402
from lessons_import import load_lesson_module  # noqa: E402

hub = load_lesson_module("L09_子智能体分工", "consult_hub")


def test_hub_delegates_and_gets_conclusions():
    main = scripted(
        call("task", "t1", description="查台风", subagent_type="typhoon-analyst"),
        "会商意见：无台风。",
    )
    subs = {"typhoon-analyst": scripted(
        call("get_typhoon_data_by_datetime", datetime="2026-07-23 08:00:00"),
        "过去 24 小时没有活动台风。")}
    r = hub.build_hub(main, subs).invoke({"messages": [{"role": "user", "content": "会商"}]})
    task_results = [m.content for m in r["messages"] if isinstance(m, ToolMessage) and m.name == "task"]
    assert task_results == ["过去 24 小时没有活动台风。"]
    # 子智能体内部的工具调用不进入中枢的消息
    assert not any(isinstance(m, ToolMessage) and m.name == "get_typhoon_data_by_datetime" for m in r["messages"])
