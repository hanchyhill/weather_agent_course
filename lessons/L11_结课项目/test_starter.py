"""冒烟测试：起点代码能在假模型下跑通“派活 → 汇总 → 暂停保存 → 批准”。"""
import os
import uuid

os.environ["COURSE_FAKE_LLM"] = "1"

from langgraph.types import Command  # noqa: E402

from common.fake import call, scripted  # noqa: E402
from common.paths import OUTPUT_DIR  # noqa: E402
from lessons_import import load_lesson_module  # noqa: E402

st = load_lesson_module("L11_结课项目", "starter_mini_consult")


def test_starter_flow():
    body = "# 标题\n" + "\n".join("# " + s + "\n……" for s in st.SECTIONS)
    main = scripted(
        call("task", "t1", description="台风", subagent_type="typhoon-analyst"),
        call("save_report", "t2", title="会商稿_test", content=body),
        "已保存。",
    )
    subs = {"typhoon-analyst": scripted(
        call("get_typhoon_data_by_datetime", datetime="2026-07-23 08:00:00"), "无活动台风。")}
    agent = st.build(main, subs)
    cfg = {"configurable": {"thread_id": str(uuid.uuid4())}}
    r = agent.invoke({"messages": [{"role": "user", "content": "会商"}]}, config=cfg)
    assert r["__interrupt__"][0].value["action_requests"][0]["name"] == "save_report"
    agent.invoke(Command(resume={"decisions": [{"type": "approve"}]}), config=cfg)
    out = OUTPUT_DIR / "会商稿_test.md"
    assert out.exists() and all(s in out.read_text(encoding="utf-8") for s in st.SECTIONS)
    out.unlink()
