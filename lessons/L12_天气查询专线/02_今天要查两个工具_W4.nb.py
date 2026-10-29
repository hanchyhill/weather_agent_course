# %% [markdown]
# # L12-2 提示词优化：问“今天”要同时查实况和预报（天气专线 W4）
#
# <!-- course-meta: real-llm -->
#
# 这一讲要用**真实模型**，`.env` 里的 `MAIN_API_KEY` 必须填好。
# 没有 API Key 时先看同目录的 `99_假模型剧本.ipynb`：那里用预设剧本演示同样的流程。
#
# 上一讲的问题：“今天”跨过了“现在”，前半天是实况、后半天是预报。
# 这一讲只改提示词，不改工具，让模型学会按时间选工具。
#
# 做法：A/B 对比两版提示词，用 `check_calls` 逐条核对模型的工具调用（该调的调了没有、窗口对不对）。

# %%
# %load_ext autoreload
# %autoreload 2

from langchain.agents import create_agent

from common import llm
from common.clock import now_bj
from common.trace import show, tool_calls
from lessons_import import load_lesson_module
from weather_tools.agent_tools import get_beijing_time

wa = load_lesson_module("L12_天气查询专线", "weather_agent")
TOOLS = [get_beijing_time, wa.geocode_place, wa.get_station_history, wa.get_forecast]
NOW = now_bj().replace(tzinfo=None)
EXPECT = wa.expected_windows(NOW)
print("现在（北京时）", NOW)
print("今天应查的实况窗口（UTC）：", EXPECT["today"]["history"])
print("今天应查的预报窗口（UTC）：", EXPECT["today"]["forecast"])

# %% [markdown]
# ## 1. 旧提示词（W1 版）

# %%
print(wa.SYSTEM_W1)

# %% [markdown]
# ## 2. 新提示词（W4 版）：多了什么？
#
# 三条规则：
# - 按时间判断选哪个工具（过去 / 未来 / 跨过现在）；
# - 跨过现在时**必须两个都查**，并写明各自的窗口；
# - 回答分两段：“截至目前的实况”“接下来的预报”。
#
# 好提示词的特点：给出**判断条件**，而不是只说“请两个都查”。

# %%
print(wa.SYSTEM_W4)

# %% [markdown]
# ## 3. 跑一遍“今天”
#
# 新提示词下，模型应该在同一轮里并行调用两个工具，再分段回答。
# （剧本里“并行调用两个工具”是什么样，见 `99_假模型剧本.ipynb`。）

# %%
model = llm.main_llm()
agent = create_agent(model=model, tools=TOOLS, system_prompt=wa.SYSTEM_W4)
r = agent.invoke({"messages": [{"role": "user", "content": "广州天河区今天的天气如何？"}]})
show(r)

# %% [markdown]
# ## 4. 自动检查工具调用
#
# 不靠肉眼读回答，直接检查模型“做了什么”：

# %%
problems = wa.check_calls(tool_calls(r), EXPECT["today"], hist_tool="get_station_history", fore_tool="get_forecast")
print("通过" if not problems else problems)

# %% [markdown]
# ## 5. 真实模型 A/B
#
# 三个问题 × 两版提示词，各跑 5 次，统计通过数。预期：旧提示词在“今天”上明显偏低。

# %%
CASES = [("广州天河区昨天的天气如何？", "yesterday"),
         ("广州天河区明天的天气如何？", "tomorrow"),
         ("广州天河区今天的天气如何？", "today")]
RUNS = 5
for name, prompt in [("旧 W1", wa.SYSTEM_W1), ("新 W4", wa.SYSTEM_W4)]:
    for q, key in CASES:
        ok = 0
        for _ in range(RUNS):
            ag = create_agent(model=llm.main_llm(), tools=TOOLS, system_prompt=prompt)
            res = ag.invoke({"messages": [{"role": "user", "content": q}]})
            ok += not wa.check_calls(tool_calls(res), EXPECT[key],
                                     hist_tool="get_station_history", fore_tool="get_forecast")
        print(f"{name}  {q}  {ok}/{RUNS}")

# %% [markdown]
# 注意：这里“窗口”仍要求模型自己把北京时换成世界时，所以昨天、明天也可能失败——
# 这是下一讲 W5 的内容。看结果时区分两类错误：**漏调工具**（W4 解决）和**窗口算错**（W5 解决）。
#
# ## 练习
#
# 1. 把规则里的“必须两个都查”删掉，只留“典型的是今天”，观察模型行为。
# 2. 用户问“广州天河区今天下午的天气”，现在是 08:30。该查什么？提示词需要补哪条规则？
# 3. 用户问“广州天河区现在的天气”呢？
