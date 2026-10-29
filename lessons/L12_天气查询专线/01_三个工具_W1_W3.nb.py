# %% [markdown]
# # L12-1 三个工具：地名 → 经纬度 → 实况 / 预报（天气专线 W1～W3）
#
# <!-- course-meta: real-llm -->
#
# 这一讲要用**真实模型**，`.env` 里的 `MAIN_API_KEY` 必须填好。
# 没有 API Key 时先看同目录的 `99_假模型剧本.ipynb`：那里用预设剧本演示同样的流程。
#
# 用户会问三个问题：
#
# 1. 广州天河区**昨天**的天气如何？
# 2. 广州天河区**明天**的天气如何？
# 3. 广州天河区**今天**的天气如何？
#
# 先不要一口气做完，一个问题一个工具往上加。离线数据是教学构造的（`data/weather/`），
# 接口形态参照 agent_dev 的 `ToolGameWeather`。课程时间固定为 `COURSE_NOW`（默认 2026-08-11 08:30）。

# %%
# %load_ext autoreload
# %autoreload 2

import json

from langchain.agents import create_agent

from common import llm
from common.clock import now_bj
from common.trace import show
from lessons_import import load_lesson_module
from weather_tools.agent_tools import get_beijing_time

wa = load_lesson_module("L12_天气查询专线", "weather_agent")
print("课程时间（北京时）：", now_bj().strftime("%Y-%m-%d %H:%M"))

# %% [markdown]
# ## W1 根据地点查询经纬度
#
# 天气接口只认经纬度，不认“天河区”。所以第一个工具把地名换成经纬度。
# 先单独试，不接模型。注意三种结果：唯一、重名、查不到。

# %%
for place in ["广州天河区", "朝阳区", "火星基地"]:
    r = json.loads(wa.geocode_place.invoke({"place": place}))
    print(place, "→", r["status"], [(c["province"], c["name"], c["lon"], c["lat"]) for c in r["candidates"]])

# %% [markdown]
# “朝阳区”北京和长春都有。工具说明里写了：`ambiguous` 时要向用户确认，不能自己挑。
# 这是工具说明（docstring）该写清楚的事，不是靠模型“聪明”。

# %% [markdown]
# ## W2 根据经纬度查询实况站点的历史数据
#
# 问题 1“昨天”是过去的天气，要查实况站点。工具参数的时间是**世界时**（和真实接口一致）。
# 北京时昨天 00:00～23:00 对应的世界时是多少？先自己算，答案在 W5 展开；这里先给出：
# 2026-08-09 16:00:00 ~ 2026-08-10 15:00:00。

# %%
r = json.loads(wa.get_station_history.invoke(
    {"lon": 113.361, "lat": 23.125, "start_time": "2026-08-09 16:00:00", "end_time": "2026-08-10 15:00:00"}))
print(r["status"], r["station"], f"距离 {r['distance_km']} km，{r['count']} 条")
print(r["summary"])

# %% [markdown]
# 看一下“没数据”时工具怎么说话：查一个未来的时间。好的工具不返回空，而是告诉模型**为什么没有、该怎么办**。

# %%
print(wa.get_station_history.invoke(
    {"lon": 113.361, "lat": 23.125, "start_time": "2026-08-12 00:00:00", "end_time": "2026-08-12 23:00:00"}))

# %% [markdown]
# 把 W1 + W2 交给智能体，问问题 1。

# %%
model = llm.main_llm()
agent = create_agent(model=model,
                     tools=[get_beijing_time, wa.geocode_place, wa.get_station_history],
                     system_prompt=wa.SYSTEM_W1)
q1 = agent.invoke({"messages": [{"role": "user", "content": "广州天河区昨天的天气如何？"}]})
show(q1)

# %% [markdown]
# ## W3 根据经纬度查询预报数据
#
# 问题 2“明天”是未来的天气，要查预报。预报工具的写法和实况几乎一样，
# 区别只有数据来源和“预报只覆盖起报时间之后”这一点——这一点要写进 docstring。

# %%
r = json.loads(wa.get_forecast.invoke(
    {"lon": 113.361, "lat": 23.125, "start_time": "2026-08-11 16:00:00", "end_time": "2026-08-12 15:00:00"}))
print(r["status"], r["grid"], "起报(UTC)", r["starttime_utc"], f"{r['count']} 条")
print(r["summary"])

# %%
TOOLS_ALL = [get_beijing_time, wa.geocode_place, wa.get_station_history, wa.get_forecast]
model = llm.main_llm()
agent = create_agent(model=model, tools=TOOLS_ALL, system_prompt=wa.SYSTEM_W1)
q2 = agent.invoke({"messages": [{"role": "user", "content": "广州天河区明天的天气如何？"}]})
show(q2)

# %% [markdown]
# ## 问题 3：今天——两个工具都不够用
#
# “今天”从 00 时到 23 时，现在是 08:30。00～08 时已经发生（要查实况），09～23 时还没发生（要查预报）。
# 只有两个独立工具和一句简单提示词时，模型很容易**只选一个**。请多问几次，看它到底怎么选。
# （想看“只查了预报”的典型错误长什么样，见 `99_假模型剧本.ipynb` 里写死的剧本。）

# %%
model = llm.main_llm()
agent = create_agent(model=model, tools=TOOLS_ALL, system_prompt=wa.SYSTEM_W1)
q3 = agent.invoke({"messages": [{"role": "user", "content": "广州天河区今天的天气如何？"}]})
show(q3)

# %% [markdown]
# 预报工具对“已经过去”的 00～08 时没有数据。如果模型只查了预报就回答“今天……”，
# 早上那段天气就漏掉了（`99_假模型剧本.ipynb` 里的剧本演示的正是这种错误）。
# **这就是 W4 要解决的问题。**

# %%
r = wa.wx.query_forecast(113.361, 23.125, "2026-08-10 16:00:00", "2026-08-11 15:00:00")
print("返回条数", r["count"], "；第一条（UTC）", r["rows"][0]["datetime"], "→ 北京时 09 时之后才有预报")

# %% [markdown]
# ## 练习
#
# 1. 让 AI 补一个测试：`geocode_place("深圳福田区")` 返回 ok，坐标接近 (114.05, 22.52)。
# 2. 把问题 1 在真实模型下问 5 次，统计传给工具的时间窗口有几次是对的
#    （`wa.check_calls` 可以帮你检查，下一讲用）。
# 3. 想一想：如果用户问“广州天河区昨天晚上的天气”，模型需要怎么算时间？
