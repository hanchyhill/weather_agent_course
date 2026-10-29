"""假模型：没有 API Key 时也能演示智能体流程。

FakeToolModel 按顺序吐出预设的回答（可以包含工具调用），
用来演示“模型决定调哪个工具 → 程序执行 → 结果交回模型”的循环。
它不会思考，只是照剧本念台词。
"""
from typing import Any

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage


class FakeToolModel(GenericFakeChatModel):
    """可以接受 bind_tools 的假模型。"""

    def bind_tools(self, tools: Any, **kwargs: Any) -> "FakeToolModel":
        return self


def scripted(*turns: AIMessage | str) -> FakeToolModel:
    """按顺序返回给定回答。字符串会被包装成普通文本回答。"""
    msgs = [t if isinstance(t, AIMessage) else AIMessage(content=t) for t in turns]
    return FakeToolModel(messages=iter(msgs))


def call(name: str, call_id: str = "call_1", **args: Any) -> AIMessage:
    """构造一条“调用工具”的模型回答。"""
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": call_id}])
