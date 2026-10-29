# %% [markdown]
# # L10-1 人工把关：保存会商稿前必须确认
#
# <!-- course-meta: real-llm -->
#
# 气象服务对外发布有责任要求。“保存/发布会商稿”“发送通知”这类工具，
# 智能体执行前必须暂停，由人确认、修改或拒绝。
#
# deepagents 用 `interrupt_on` 指定哪些工具要人工确认；需要 `checkpointer` 记住暂停时的状态。
#
# 运行方式：在 VS Code 或 Jupyter 中逐格运行（Shift+Enter）。这一讲要用**真实模型**，
# `.env` 里的 `MAIN_API_KEY` 必须填好。
# 暂时没有 Key，就先看 `99_假模型剧本.ipynb`：那里用预设剧本演示同样的流程。

# %%
# 改了 common/、weather_tools/ 里的代码后自动重新加载，不用重启内核
# %load_ext autoreload
# %autoreload 2

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
        system_prompt="你是会商助手。写好会商稿后调用 save_report 保存。用户拒绝保存时，如实告知未保存。",
        interrupt_on={"save_report": {"allowed_decisions": ["approve", "edit", "reject"]}},
        checkpointer=InMemorySaver(),
    )


DRAFT = "# 早间会商\n过去 24 小时无活动台风……"

# %% [markdown]
# ## 1. 暂停：智能体要保存，先停下来等人

# %%
agent = build(llm.main_llm())
cfg = {"configurable": {"thread_id": str(uuid.uuid4())}}
r = agent.invoke({"messages": [{"role": "user", "content": "把这份会商稿保存下来：" + DRAFT}]}, config=cfg)

req = r["__interrupt__"][0].value["action_requests"][0]
print("待确认的操作：", req["name"])
print("参数：", req["args"])

# %% [markdown]
# ## 2. 三种处理
#
# | 决定 | 写法 | 效果 |
# |---|---|---|
# | 批准 | `{"type": "approve"}` | 按原参数执行 |
# | 修改 | `{"type": "edit", "edited_action": {"name": ..., "args": {...}}}` | 按修改后的参数执行 |
# | 拒绝 | `{"type": "reject", "message": "原因"}` | 不执行，把原因告诉智能体 |
#
# 改下面的 `decision` 试三种情况。

# %%
decision = {"type": "edit", "edited_action": {
    "name": "save_report", "args": {"title": "早间会商_已审核", "content": DRAFT + "\n\n（值班首席已审核）"}}}
# decision = {"type": "approve"}
# decision = {"type": "reject", "message": "台风资料时次不对，先不要保存"}

r2 = agent.invoke(Command(resume={"decisions": [decision]}), config=cfg)
show(r2, max_tool_chars=200)

# %% [markdown]
# 注意：模型说的话和工具实际做的事可能不一致。最后一行打印 `outputs/` 里的文件，
# 那才是真的发生了什么。
#
# `99_假模型剧本.ipynb` 里有反例：剧本写死“已保存”，所以拒绝之后模型仍会说“已保存”；
# 真实模型会读到“用户拒绝”的消息并如实回答。
# 这也提醒我们：**不能只看模型说了什么，要看工具实际做了什么**。

# %%
print(sorted(p.name for p in OUTPUT_DIR.glob("早间会商*.md")))
