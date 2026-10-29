# %% [markdown]
# # L12-3 北京时与世界时：改提示词，还是改工具？（天气专线 W5）
#
# <!-- course-meta: real-llm -->
#
# 这一讲要用**真实模型**，`.env` 里的 `MAIN_API_KEY` 必须填好。
# 没有 API Key 时先看同目录的 `99_假模型剧本.ipynb`：那里用预设剧本演示同样的流程。
#
# 用户说“昨天”“明天”，指的是**北京时**的自然日。接口的时间是**世界时**。
# 北京时 2026-08-10 00:00 = 世界时 2026-08-09 16:00，查“昨天”要跨两个世界时日期，最容易错。
#
# 两个办法：
# - **方案 A 改提示词**：把换算规则写进提示词，让模型心算。
# - **方案 B 改工具**：新工具直接收北京时，换算由程序做，返回里再补 `time_bj`。
#
# 这一讲让两个方案对打，再看哪个可靠。

# %%
# %load_ext autoreload
# %autoreload 2

import json

from langchain.agents import create_agent

from common import llm
from common.clock import now_bj
from common.trace import show, tool_calls
from lessons_import import load_lesson_module
from weather_tools.agent_tools import get_beijing_time

wa = load_lesson_module("L12_天气查询专线", "weather_agent")
NOW = now_bj().replace(tzinfo=None)
EXPECT = wa.expected_windows(NOW)

# %% [markdown]
# ## 1. 先看错在哪
#
# 模型把“昨天”当成世界时直接传（忘了减 8 小时）会怎样？

# %%
wrong = json.loads(wa.get_station_history.invoke(
    {"lon": 113.361, "lat": 23.125, "start_time": "2026-08-10 00:00:00", "end_time": "2026-08-10 23:00:00"}))
right = json.loads(wa.get_station_history.invoke(
    {"lon": 113.361, "lat": 23.125, "start_time": "2026-08-09 16:00:00", "end_time": "2026-08-10 15:00:00"}))
print("忘了换算：", wrong["summary"])
print("换算正确：", right["summary"])

# %% [markdown]
# 昨天的雷阵雨在北京时 15～17 时 = 世界时 07～09 时，恰好落在“忘了换算”的窗口里，
# 所以降水总量看起来差不多；但气温极值、日期边界都错了一截（取到的是北京时 8/10 08 时到 8/11 07 时）。
# **结果“看起来差不多”最危险**，要靠检查函数而不是肉眼。
#
# 再看回答时间：工具返回的是世界时，模型如果直接说“降水出现在 07～09 时”，用户会以为是早上。

# %%
print([(r["datetime"], r["rain"]) for r in right["rows"] if r["rain"] > 0])

# %% [markdown]
# ## 2. 方案 A：只改提示词

# %%
print(wa.SYSTEM_W5_PROMPT[-300:])

# %% [markdown]
# 优点：不用改代码。缺点：每次都靠模型心算；回答时还要“加 8 小时换回去”，两头都可能错。

# %%
TOOLS_A = [get_beijing_time, wa.geocode_place, wa.get_station_history, wa.get_forecast]
model = llm.main_llm()
agent = create_agent(model=model, tools=TOOLS_A, system_prompt=wa.SYSTEM_W5_PROMPT)
ra = agent.invoke({"messages": [{"role": "user", "content": "广州天河区昨天的天气如何？"}]})
print(wa.check_calls(tool_calls(ra), EXPECT["yesterday"], hist_tool="get_station_history",
                     fore_tool="get_forecast") or "方案 A：窗口正确")

# %% [markdown]
# ## 3. 方案 B：改工具
#
# `get_station_history_bj` / `get_forecast_bj`：
# - 入参是北京时，`bj_range_to_utc` 在程序里减 8 小时；
# - 返回的每条记录补 `time_bj`，回答只用它；
# - docstring 明确写“直接传，不要自己换算”。
#
# 模型要做的事从“算时差”变成“把‘昨天’变成昨天 00:00～23:00”，后者是自然语言理解，模型擅长得多。

# %%
r = json.loads(wa.get_station_history_bj.invoke(
    {"lon": 113.361, "lat": 23.125, "start_time": "2026-08-10 00:00:00", "end_time": "2026-08-10 23:00:00"}))
print(r["time_zone"])
print([(x["time_bj"], x["rain"]) for x in r["rows"] if x["rain"] > 0])
print(r["summary"] == right["summary"], "（与方案 A 手工换算的统计一致）")

# %%
TOOLS_B = [get_beijing_time, wa.geocode_place, wa.get_station_history_bj, wa.get_forecast_bj]
model = llm.main_llm()
agent = create_agent(model=model, tools=TOOLS_B, system_prompt=wa.SYSTEM_W5_TOOL)
rb = agent.invoke({"messages": [{"role": "user", "content": "广州天河区今天的天气如何？"}]})
show(rb)
print(wa.check_calls(tool_calls(rb), EXPECT["today"], hist_tool="get_station_history_bj",
                     fore_tool="get_forecast_bj", bj_args=True) or "方案 B：窗口正确")

# %% [markdown]
# ## 4. 真实模型对比
#
# 三个问题 × 方案 A / B，各 5 次。预期 B 明显高于 A。

# %%
CASES = [("广州天河区昨天的天气如何？", "yesterday"),
         ("广州天河区明天的天气如何？", "tomorrow"),
         ("广州天河区今天的天气如何？", "today")]
RUNS = 5
for name, tools, prompt, h, f, bj in [
    ("A 改提示词", TOOLS_A, wa.SYSTEM_W5_PROMPT, "get_station_history", "get_forecast", False),
    ("B 改工具", TOOLS_B, wa.SYSTEM_W5_TOOL, "get_station_history_bj", "get_forecast_bj", True),
]:
    for q, key in CASES:
        ok = 0
        for _ in range(RUNS):
            ag = create_agent(model=llm.main_llm(), tools=tools, system_prompt=prompt)
            res = ag.invoke({"messages": [{"role": "user", "content": q}]})
            ok += not wa.check_calls(tool_calls(res), EXPECT[key], hist_tool=h, fore_tool=f, bj_args=bj)
        print(f"{name}  {q}  {ok}/{RUNS}")

# %% [markdown]
# ## 5. 小结：怎么选
#
# | | 方案 A 改提示词 | 方案 B 改工具 |
# |---|---|---|
# | 换算由谁做 | 模型心算 | 程序 |
# | 回答时的时间 | 模型要再加 8 小时 | 工具直接给 `time_bj` |
# | 可靠性 | 看模型心情 | 确定 |
# | 代价 | 零 | 多写一层小工具 |
#
# 原则：**必须百分之百对的事交给程序，提示词只管需要判断的事。**
# 和台风专线 L5 的结论一致（T1→T2）。底层世界时函数保留不动，BJ 版只是外面包一层。
#
# ## 练习
#
# 1. 用户问“昨天晚上 8 点到 11 点”，方案 B 下模型该传什么？
# 2. 让 AI 给 `bj_range_to_utc` 补测试：跨月（8/1 00:00 → 7/31 16:00）、跨年。
# 3. 如果接口哪天改成直接收北京时，方案 B 要改几处？方案 A 呢？
