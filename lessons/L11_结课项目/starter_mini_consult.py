"""结课项目起点：迷你会商助手。

各组在这个文件基础上完成。已经搭好的部分：
- 中枢 + 台风组 + 实况组（复用 L9 的 consult_hub）
- 保存会商稿前人工确认（L10）
- 命令行运行与“更换当前时间”

需要各组完成（搜索 TODO）：
1. 补齐会商稿五节的子智能体或工具（降水、形势、气温趋势等）
2. 至少 2 个本组编写的 Skill（放在 skills/ 下）
3. 中枢提示词按五节结构输出
4. 本组的时间测试用例（tests 或本目录下 test_*.py）

运行：
    uv run python "lessons/L11_结课项目/starter_mini_consult.py"
    uv run python "lessons/L11_结课项目/starter_mini_consult.py" --now "2026-07-23 08:30"
"""
import argparse
import uuid

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from common.paths import COURSE_ROOT, OUTPUT_DIR
from lessons_import import load_lesson_module

hub = load_lesson_module("L09_子智能体分工", "consult_hub")

SECTIONS = [
    "1. 过去24小时天气实况",
    "2. 未来5天天气形势概览",
    "3. 主要天气成因分析",
    "4. 最高/最低气温逐日变化趋势",
    "5. 关注建议",
]

HUB_PROMPT = hub.HUB_PROMPT + f"""
## 会商稿格式
第一行用一级标题概括最值得关注的天气。正文分五节，标题依次为：
{chr(10).join('# ' + s for s in SECTIONS)}
第 5 节末尾写“资料缺口”和“参考图片”。
日期写成“8 月 11 日”，不要写 day0、day1 这类内部写法。
写完后调用 save_report 保存，标题用“会商稿_YYYYMMDD”。
"""
# TODO 各组：按本组分工修改中枢提示词


@tool
def save_report(title: str, content: str) -> str:
    """保存会商稿。保存前需人工确认。"""
    OUTPUT_DIR.mkdir(exist_ok=True)
    path = OUTPUT_DIR / f"{title}.md"
    path.write_text(content, encoding="utf-8")
    return f"已保存到 {path}"


def build(model=None, sub_models=None):
    from common import llm
    specs = hub.subagent_specs(sub_models)
    # TODO 各组：在这里追加本组的子智能体，例如 specs.append({...})
    return create_deep_agent(
        model=model or llm.main_llm(),
        tools=[hub.get_beijing_time, save_report],
        system_prompt=HUB_PROMPT,
        subagents=specs,
        skills=["/skills/"],
        backend=FilesystemBackend(root_dir=str(COURSE_ROOT), virtual_mode=True),
        interrupt_on={"save_report": {"allowed_decisions": ["approve", "edit", "reject"]}},
        checkpointer=InMemorySaver(),
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--now", help="覆盖课程当前北京时间，格式 YYYY-MM-DD HH:MM")
    args = ap.parse_args()
    if args.now:
        from common.clock import set_course_now
        set_course_now(args.now)
    agent = build()
    cfg = {"configurable": {"thread_id": str(uuid.uuid4())}}
    r = agent.invoke({"messages": [{"role": "user", "content": "请准备今天的早间会商材料。"}]}, config=cfg)
    while r.get("__interrupt__"):
        req = r["__interrupt__"][0].value["action_requests"][0]
        print("\n===== 待确认的会商稿 =====\n")
        print(req["args"].get("content", ""))
        ans = input("\n保存吗？[y 保存 / n 拒绝]：").strip().lower()
        decision = {"type": "approve"} if ans == "y" else {"type": "reject", "message": "值班首席未同意保存"}
        r = agent.invoke(Command(resume={"decisions": [decision]}), config=cfg)
    print(r["messages"][-1].text)


if __name__ == "__main__":
    main()
