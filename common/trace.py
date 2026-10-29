"""把智能体的运行过程打印成预报员看得懂的样子。"""
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage


def _text(content) -> str:
    if isinstance(content, str):
        return content
    parts = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text", ""))
    return "".join(parts)


def show(result: dict, *, max_tool_chars: int = 600) -> None:
    """逐条打印消息：用户提问、模型调用工具、工具返回、最终回答。"""
    for i, m in enumerate(result["messages"], 1):
        if isinstance(m, HumanMessage):
            print(f"[{i}] 用户：{_text(m.content)}")
        elif isinstance(m, AIMessage) and m.tool_calls:
            for tc in m.tool_calls:
                print(f"[{i}] 模型决定调用工具 {tc['name']}，参数 {tc['args']}")
        elif isinstance(m, ToolMessage):
            body = _text(m.content)
            if len(body) > max_tool_chars:
                body = body[:max_tool_chars] + f"……（共 {len(body)} 字，已截断）"
            print(f"[{i}] 工具 {m.name} 返回：{body}")
        elif isinstance(m, AIMessage):
            print(f"[{i}] 模型回答：{_text(m.content)}")
        print()


def final_text(result: dict) -> str:
    """取最后一条模型回答的文字。"""
    for m in reversed(result["messages"]):
        if isinstance(m, AIMessage) and not m.tool_calls:
            return _text(m.content)
    return ""


def tool_calls(result: dict) -> list[dict]:
    """列出本次运行中所有的工具调用（名字和参数）。"""
    calls = []
    for m in result["messages"]:
        if isinstance(m, AIMessage):
            calls.extend({"name": tc["name"], "args": tc["args"]} for tc in m.tool_calls)
    return calls
