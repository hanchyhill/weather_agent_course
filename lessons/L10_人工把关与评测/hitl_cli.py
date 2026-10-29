"""L10 HITL 命令行练习：在课程根目录运行 uv run python lessons/L10_人工把关与评测/hitl_cli.py。"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# 改了 common/、weather_tools/ 里的代码后自动重新加载，不用重启内核

import uuid

from deepagents import create_deep_agent
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from common import llm
from common.paths import OUTPUT_DIR
from common.trace import show


@tool
def save_report(title: str, content: str) -> str:
    """把会商稿保存为 Markdown 文件。保存前需人工确认。"""
    OUTPUT_DIR.mkdir(exist_ok=True)
    path = OUTPUT_DIR / f"{title}.md"
    path.write_text(content, encoding="utf-8")
    return f"已保存到 {path.name}"


def build(model):
    return create_deep_agent(
        model=model,
        tools=[save_report],
        system_prompt=("你是会商助手。写好会商稿后调用 save_report 保存。"
                       "人工审核时可以修改标题和正文；审核后的参数代表用户的最终决定，"
                       "不应视为错误、未授权或需要重新保存，也不要重新发起原调用。"
                       "以 save_report 的实际工具返回为准，准确说明保存结果；"
                       "不要用其他文件检索工具核验保存结果。用户拒绝保存时如实告知未保存。"),
        interrupt_on={"save_report": {"allowed_decisions": ["approve", "edit", "reject"]}},
        checkpointer=InMemorySaver(),
    )


DRAFT = "# 早间会商\n过去 24 小时无活动台风……"

def ask_decision(request):
    """展示一个待执行操作，并通过输入获取人工决定。"""
    print(f"\n待审核工具：{request['name']}")
    print("待审核参数：")
    for key, value in request["args"].items():
        print(f"  {key}:\n{value}" if key == "content" else f"  {key}: {value}")

    while True:
        choice = input("请选择 [a] 批准 / [e] 修改 / [r] 拒绝：").strip().lower()
        if choice == "a":
            return {"type": "approve"}
        if choice == "r":
            reason = input("拒绝原因（可留空）：").strip() or "人工审核未通过"
            return {"type": "reject", "message": reason}
        if choice == "e":
            if request["name"] != "save_report":
                print("该示例只支持修改 save_report 的参数，请选择批准或拒绝。")
                continue
            args = dict(request["args"])
            title = input(f"新标题（直接回车保留 {args['title']}）：").strip()
            if title:
                args["title"] = title
            print("请输入新的正文，每行回车；单独输入 . 结束，直接输入 . 保留原文：")
            lines = []
            while True:
                line = input()
                if line == ".":
                    break
                lines.append(line)
            if lines:
                args["content"] = "\n".join(lines)
            print(f"修改后的标题：{args['title']}\n修改后的正文：\n{args['content']}")
            confirm = input("按修改后的内容执行？[y/N]：").strip().lower()
            if confirm == "y":
                return {"type": "edit", "edited_action": {"name": request["name"], "args": args}}
            print("未确认修改，请重新选择。")
            continue
        print("无效选择，请输入 a、e 或 r。")


def run_hitl(agent, user_request):
    """启动独立会话，循环处理暂停，直到智能体完成。"""
    cfg = {"configurable": {"thread_id": str(uuid.uuid4())}}
    result = agent.invoke({"messages": [{"role": "user", "content": user_request}]}, config=cfg)
    while result.get("__interrupt__"):
        interrupts = result["__interrupt__"]
        if len(interrupts) != 1:
            raise RuntimeError(f"遇到 {len(interrupts)} 个并发中断，本示例无法安全处理。")
        requests = interrupts[0].value["action_requests"]
        decisions = [ask_decision(request) for request in requests]
        result = agent.invoke(Command(resume={"decisions": decisions}), config=cfg)
    print("\n智能体运行结果：")
    show(result, max_tool_chars=500)
    return result



def main():
    parser = argparse.ArgumentParser(description="人工审核会商稿保存操作")
    parser.add_argument("--fake", action="store_true", help="使用假模型演示，无需 API Key")
    args = parser.parse_args()
    if args.fake:
        from common.fake import call, scripted
        model = scripted(call("save_report", title="早间会商", content=DRAFT), "本次审核流程已结束，请查看工具返回。")
        print("假模型模式：工具调用和文件保存是真实的。")
    else:
        model = llm.main_llm()
    try:
        run_hitl(build(model), "把这份会商稿保存下来：" + DRAFT)
    except (EOFError, KeyboardInterrupt):
        print("\n交互已中止；未确认的操作不会继续执行。")


if __name__ == "__main__":
    main()
