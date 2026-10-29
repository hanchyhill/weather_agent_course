# %% [markdown]
# # L5 附：假模型剧本（T2～T4 的智能体那一节）
#
# 这一份是 `02_台风北京时与回查_T2_T4.ipynb` 最后一节的**剧本版**，给还没配好 Key 的学员看流程。
#
# 三点要说清：
#
# 1. 这里模型**不会思考**，只是照剧本念台词。剧本写在代码里（`llm.agent_model(...)` 的参数），不是模型自己想出来的。
# 2. 工具调用、消息顺序和真实模型一样，可以照着看懂“先查台风，查不到就如实说没有”。
# 3. 想知道模型**自己**会不会忍住不去查路径图，必须回 `02_台风北京时与回查_T2_T4.ipynb` 用真实模型。
#
# `01_起报时次与时效.ipynb` 全是时间换算，不调用模型，所以没有剧本版，直接跑就行。

# %%
import os

# 这一份专门演假模型，强制打开（不依赖 .env 的设置）
os.environ["COURSE_FAKE_LLM"] = "1"

from langchain.agents import create_agent

from common import llm
from common.fake import call
from common.trace import show, tool_calls
from weather_tools import typhoon
from weather_tools.agent_tools import get_beijing_time, get_typhoon_data_by_datetime

print("FAKE 模式" if llm.use_fake_llm() else "真实模型模式")

# %% [markdown]
# ## 1. 先看工具本身（这一段是真的）
#
# 和正式 notebook 的 T4 一样，四种情形：有时次命中、要回查好久、24 小时内没台风。全是本地数据，没有模型参与。

# %%
for q in ["2026-08-11 08:00:00", "2026-07-29 08:00:00", "2026-07-23 08:00:00", "2026-09-01 08:00:00"]:
    r = typhoon.query_typhoon_with_lookback(q)
    if "query_metadata" in r:
        m = r["query_metadata"]
        print(q, "→ 命中", m["actual_datetime_bj"], f"回查 {m['lookback_hours']} 小时", "tsid", r["tsid"])
    elif r.get("status") == "not_applicable":
        print(q, "→ 24 小时内无台风，尝试", len(r["query_attempts"]), "次")
    else:
        print(q, "→ 结构不认识，原样返回", r)

# %% [markdown]
# ## 2. 这是剧本：接到智能体上，无台风要如实回答
#
# 剧本三步：先看时间 → 再查 7 月 23 日 08 时的台风 → 按“过去 24 小时没有”作答。
#
# 注意：**“查完台风就不再查路径图”这个决定也是剧本写死的**，所以这一节只能看流程形状，看不出模型自己会不会多此一举。

# %%
SYSTEM = """你是广东省气象台的台风值班助手。
- 用户说的时间都是北京时。查询台风时直接传北京时，不要自己加减 8 小时。
- 台风查询返回 status 为 not_applicable 时，如实回答“过去 24 小时没有活动台风”，不要再调用其他台风工具。"""

model = llm.agent_model(
    call("get_beijing_time"),
    call("get_typhoon_data_by_datetime", "call_2", datetime="2026-07-23 08:00:00"),
    "截至北京时 7 月 23 日 08 时，过去 24 小时西北太平洋没有活动台风。",
)
agent = create_agent(model=model, tools=[get_beijing_time, get_typhoon_data_by_datetime], system_prompt=SYSTEM)
r = agent.invoke({"messages": [{"role": "user", "content": "2026 年 7 月 23 日早上 8 点有台风吗？"}]})
show(r, max_tool_chars=300)
print([c["name"] for c in tool_calls(r)])

# %% [markdown]
# 读轨迹：[1] 提问 → [2] 查时间 → [3] 查台风（返回 not_applicable）→ [4] 模型回答“没有”。
#
# 真模型下这题值得多看几眼：它会不会查完还去要 tsid 取路径图？

# %% [markdown]
# ## 3. 7 月 29 日那题（"回查 21 小时"的样子）
#
# 这一格只跑工具，不涉及模型：7 月 29 日 08 时没有资料，工具往前推到 7 月 27 日 11 时才查到台风红霞。
# 正式 notebook 里由真实模型把这段说给用户听；剧本册里它只是数字，别把它当成模型的推理。

# %%
r = typhoon.query_typhoon_with_lookback("2026-07-29 08:00:00")
m = r["query_metadata"]
print("命中时次（北京时）：", m["actual_datetime_bj"], f"，回查 {m['lookback_hours']} 小时，tsid", r["tsid"])
print(typhoon.summarize(r))

# %% [markdown]
# 配好 Key 之后回 `02_台风北京时与回查_T2_T4.ipynb`：模型自己决定查什么、怎么表述，才是这一讲要体会的东西。
