# %% [markdown]
# # L1 附：没有 API Key 也能看流程（假模型）
#
# 这个 notebook 是 `01_第一个智能体.ipynb` 的**假模型版**，专门给还没配好 Key 的学员熟悉流程。
#
# 三点要说清：
#
# 1. 这里模型**不会思考**，只是照剧本念台词。剧本写在代码里（`llm.agent_model(...)` 的参数），不是模型自己想出来的。
# 2. 轨迹结构、消息顺序和真实模型一样，可以照着看懂“智能体循环”。
# 3. 想问出自己的问题、想体会 docstring 的影响，必须回 `01_第一个智能体.ipynb` 用真实模型。

# %%
import os

# 这一讲专门演假模型，强制打开（不依赖 .env 的设置）
os.environ["COURSE_FAKE_LLM"] = "1"

from langchain.agents import create_agent
from langchain_core.tools import tool

from common import llm
from common.clock import now_bj
from common.fake import call
from common.trace import show

print("FAKE 模式" if llm.use_fake_llm() else "真实模型模式")

# %% [markdown]
# ## 1. 只有模型
#
# 没有工具时，模型只能老实说不知道。真实模型下这句是它自己说的，这里是剧本写好的。

# %%
print(llm.ask("现在北京时间几点？今天适合做哪个时次的早间会商？",
              fake_answer="抱歉，我无法获取当前时间。"))

# %% [markdown]
# ## 2. 给模型一个工具
#
# 剧本第一步调 `get_beijing_time`，第二步按工具结果回答。程序只负责执行工具、把结果交回去。

# %%
@tool
def get_beijing_time() -> str:
    """获取当前北京时间，格式 YYYY-MM-DD HH:MM。回答与“现在”“今天”有关的问题前先调用。"""
    return now_bj().strftime("%Y-%m-%d %H:%M")


model = llm.agent_model(
    call("get_beijing_time"),
    "现在是北京时间 2026-08-11 08:30，适合准备 08 时资料的早间会商。",
)
agent = create_agent(
    model=model,
    tools=[get_beijing_time],
    system_prompt="你是广东省气象台的值班助手，用中文简洁回答。",
)
show(agent.invoke({"messages": [{"role": "user", "content": "现在几点？今天适合做哪个时次的早间会商？"}]}))

# %% [markdown]
# 读轨迹：[1] 提问 → [2] 模型决定调用工具 → [3] 工具返回 → [4] 模型回答。
#
# 注意：**“决定调用”这一步在假模型里也是剧本写死的**。所以这一节只能看流程结构，看不出“模型会不会自己想到用工具”。

# %% [markdown]
# ## 3. 说明写得含糊会怎样（假模型看不到效果）
#
# 真实模型下，说明只有“时间”两个字时可能就不调用了。假模型照样按剧本走，所以这一节在这里只是演示“轨迹长什么样”。
#
# 另外把工具改成返回**世界时**，看看剧本里的模型会不会把世界时当北京时报出去。

# %%
from common.clock import UTC


@tool
def get_time_vague() -> str:
    """时间"""
    return now_bj().astimezone(UTC).strftime("%Y-%m-%d %H:%M")


model = llm.agent_model(call("get_time_vague"), "现在是 2026-08-11 00:30。")
agent = create_agent(model=model, tools=[get_time_vague],
                     system_prompt="你是广东省气象台的值班助手，用中文简洁回答。")
show(agent.invoke({"messages": [{"role": "user", "content": "现在几点？"}]}))

print("对照——北京时：", now_bj().strftime("%Y-%m-%d %H:%M"),
      "世界时：", get_time_vague.invoke({}))

# %% [markdown]
# ## 4. 区县工具
#
# 内容和正式 notebook 第 4 节一样，只是模型的回答换成剧本。

# %%
import pandas as pd

from common.paths import DATA_DIR

GEO = pd.read_csv(DATA_DIR / "tmax_desc" / "地理划分_去除空列.csv")


@tool
def find_city_of_county(county: str) -> str:
    """查询广东某个区县所属的地市和所在分区。

    参数 county：区县名称，可以带或不带“市/县/区”，例如“连州”或“连州市”。
    """
    hit = GEO[GEO["区县"].str.startswith(county.rstrip("市县区"))]
    if hit.empty:
        return f"没有找到区县：{county}"
    row = hit.iloc[0]
    return f"{row['区县']} 属于 {row['分区1']}，位于{row['行政区划']}（{row['分区2']}）"


print(find_city_of_county.invoke({"county": "连州"}))

# %%
model = llm.agent_model(
    call("find_city_of_county", county="连州"),
    "连州属于清远市，位于粤北。",
)
agent = create_agent(model=model, tools=[get_beijing_time, find_city_of_county],
                     system_prompt="你是广东省气象台的值班助手，用中文简洁回答。")
show(agent.invoke({"messages": [{"role": "user", "content": "连州属于哪个市？"}]}))

# %% [markdown]
# ## 5. deepagents 的那一套，假模型也能看
#
# 同一个问题问两个框架。回答是剧本，但下面的**探针**是真的：它不调模型，只记录被绑定了哪些工具。

# %%
from deepagents import create_deep_agent

TOOLS = [get_beijing_time, find_city_of_county]
PROMPT = "你是广东省气象台的值班助手，用中文简洁回答。"
QUESTION = "你能使用哪些工具？"

plain_agent = create_agent(
    model=llm.agent_model(
        "我能用 get_beijing_time 查当前北京时间，用 find_city_of_county 查广东区县属于哪个地市。"
    ),
    tools=TOOLS,
    system_prompt=PROMPT,
)
deep_agent = create_deep_agent(
    model=llm.agent_model(
        "除了 get_beijing_time 和 find_city_of_county，我还能用 ls、read_file、write_file、edit_file、delete、"
        "glob、grep 读写文件，用 task 派活给子智能体。"
    ),
    tools=TOOLS,
    system_prompt=PROMPT,
)

for name, agent in [("create_agent", plain_agent), ("create_deep_agent", deep_agent)]:
    print(f"===== {name} =====")
    show(agent.invoke({"messages": [{"role": "user", "content": QUESTION}]}))

# %%
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult


class ToolSpy(BaseChatModel):
    """不调用任何模型接口：只记录被绑定了哪些工具，然后回一句话。"""

    seen: list[str] = []

    @property
    def _llm_type(self) -> str:
        return "tool-spy"

    def bind_tools(self, tools, **kwargs):
        if not self.seen:
            self.seen = sorted(getattr(t, "name", str(t)) for t in tools)
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content="我看看我的工具。"))])


for name, build in [
    ("create_agent", lambda m: create_agent(model=m, tools=TOOLS, system_prompt=PROMPT)),
    ("create_deep_agent", lambda m: create_deep_agent(model=m, tools=TOOLS, system_prompt=PROMPT)),
]:
    spy = ToolSpy()
    build(spy).invoke({"messages": [{"role": "user", "content": QUESTION}]})
    print(f"{name} 绑定的工具（{len(spy.seen)} 个）：{spy.seen}")

# %% [markdown]
# 探针这一格和真实模型无关，结论可以直接用：`create_agent` 绑 2 个，`create_deep_agent` 绑 10 个（多出 8 个内置工具）。
#
# 配好 Key 之后回 `01_第一个智能体.ipynb`，模型自己说的话、自己做的决定，才是这一讲要体会的东西。
