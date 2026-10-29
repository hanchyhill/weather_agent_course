# %% [markdown]
# # L12 附：假模型剧本册（天气专线 W1～W5）
#
# 这个 notebook 把 `01_三个工具_W1_W3.ipynb`、`02_今天要查两个工具_W4.ipynb`、
# `03_北京时与世界时_W5.ipynb` 里删掉的**剧本**集中复现，按 W1～W5 分节。
#
# 三点要说清：
#
# 1. 这里的模型**不会思考**，只是照剧本念台词。台词写在代码里（`llm.agent_model(...)` 的参数），不是模型自己想出来的。
# 2. 轨迹结构、消息顺序、工具调用和工具返回都是**真的**，只有“决策”不是模型做的。
# 3. 想体会真实的工具选择、真实的时区换算，请回 `01` / `02` / `03` 三个正式 notebook 用真实模型跑。

# %%
import os

# 这一讲专门演假模型，强制打开（不依赖 .env 的设置）
os.environ["COURSE_FAKE_LLM"] = "1"

from langchain.agents import create_agent
from langchain_core.messages import AIMessage

from common import llm
from common.clock import now_bj
from common.fake import call
from common.trace import show, tool_calls
from lessons_import import load_lesson_module
from weather_tools.agent_tools import get_beijing_time

wa = load_lesson_module("L12_天气查询专线", "weather_agent")
TOOLS_ALL = [get_beijing_time, wa.geocode_place, wa.get_station_history, wa.get_forecast]
NOW = now_bj().replace(tzinfo=None)
EXPECT = wa.expected_windows(NOW)
print("FAKE 模式" if llm.use_fake_llm() else "真实模型模式")

# %% [markdown]
# ## W1～W2 昨天：地名 → 经纬度 → 实况
#
# **这是剧本**：模型先查北京时间，再换经纬度，再查实况窗口，最后按工具结果回答。
# 换成真实模型后，它会不会先调 `get_beijing_time`、窗口算得对不对，都要靠 `check_calls` 检查。

# %%
model = llm.agent_model(
    call("get_beijing_time"),
    call("geocode_place", "c2", place="广州天河区"),
    call("get_station_history", "c3", lon=113.361, lat=23.125,
         start_time="2026-08-09 16:00:00", end_time="2026-08-10 15:00:00"),
    "广州天河区昨天下午出现雷阵雨：15～17 时累计降水约 19.9 毫米，其中 16 时雨最大（12.6 毫米）；"
    "气温 23.8～33.8℃，阵风最大约 13 米/秒（6 级）。",
)
agent = create_agent(model=model,
                     tools=[get_beijing_time, wa.geocode_place, wa.get_station_history],
                     system_prompt=wa.SYSTEM_W1)
q1 = agent.invoke({"messages": [{"role": "user", "content": "广州天河区昨天的天气如何？"}]})
show(q1)

# %% [markdown]
# ## W3 明天：查预报
#
# **这是剧本**：同样的三步，最后一步换成 `get_forecast`，窗口是明天的北京时自然日换算成世界时。

# %%
model = llm.agent_model(
    call("get_beijing_time"),
    call("geocode_place", "c2", place="广州天河区"),
    call("get_forecast", "c3", lon=113.361, lat=23.125,
         start_time="2026-08-11 16:00:00", end_time="2026-08-12 15:00:00"),
    "广州天河区明天午后有中到大雨：14～18 时累计降水约 45 毫米，16 时雨最大；气温 24～33℃。出门请带伞，避开午后出行。",
)
agent = create_agent(model=model, tools=TOOLS_ALL, system_prompt=wa.SYSTEM_W1)
q2 = agent.invoke({"messages": [{"role": "user", "content": "广州天河区明天的天气如何？"}]})
show(q2)

# %% [markdown]
# ## W3 问题 3：今天——模型只选了一个工具（典型错误）
#
# **这是剧本**：只有两个独立工具和一句简单提示词时，模型容易只查预报。
# 这里演的就是“漏掉早上那段实况”的样子。真实模型下请多问几次，看它到底怎么选。

# %%
model = llm.agent_model(
    call("get_beijing_time"),
    call("geocode_place", "c2", place="广州天河区"),
    call("get_forecast", "c3", lon=113.361, lat=23.125,
         start_time="2026-08-10 16:00:00", end_time="2026-08-11 15:00:00"),
    "广州天河区今天傍晚有阵雨，累计降水约 8.5 毫米。",
)
agent = create_agent(model=model, tools=TOOLS_ALL, system_prompt=wa.SYSTEM_W1)
q3 = agent.invoke({"messages": [{"role": "user", "content": "广州天河区今天的天气如何？"}]})
show(q3)
print(wa.check_calls(tool_calls(q3), EXPECT["today"],
                     hist_tool="get_station_history", fore_tool="get_forecast") or "通过")

# %% [markdown]
# 检查函数报了“漏调了 get_station_history”——这是 W4 要解决的问题。剧本里模型只挑了一个工具，所以必然报错。

# %% [markdown]
# ## W4：新提示词，一轮并行调两个工具（理想行为）
#
# **这是剧本**：新提示词下模型在**同一轮**里并行调 `get_station_history` 和 `get_forecast`，再分两段回答。
# 真实模型会不会这样，请到 `02_今天要查两个工具_W4.ipynb` 的 A/B 单元去看通过数。

# %%
two_calls = AIMessage(content="", tool_calls=[
    {"name": "get_station_history", "id": "c3",
     "args": {"lon": 113.361, "lat": 23.125, "start_time": "2026-08-10 16:00:00", "end_time": "2026-08-11 00:00:00"}},
    {"name": "get_forecast", "id": "c4",
     "args": {"lon": 113.361, "lat": 23.125, "start_time": "2026-08-11 01:00:00", "end_time": "2026-08-11 15:00:00"}},
])
model = llm.agent_model(
    call("get_beijing_time"),
    call("geocode_place", "c2", place="广州天河区"),
    two_calls,
    "【截至目前的实况】今天凌晨到早上天河区以多云到晴为主，没有降水，气温约 24～28℃。\n"
    "【接下来的预报】傍晚 17～18 时有阵雨，累计约 8.5 毫米；白天最高约 33℃。出门带伞，避开傍晚高峰。",
)
agent = create_agent(model=model, tools=TOOLS_ALL, system_prompt=wa.SYSTEM_W4)
r = agent.invoke({"messages": [{"role": "user", "content": "广州天河区今天的天气如何？"}]})
show(r)
print(wa.check_calls(tool_calls(r), EXPECT["today"],
                     hist_tool="get_station_history", fore_tool="get_forecast") or "窗口正确")

# %% [markdown]
# ## W5 方案 A：只改提示词，靠模型心算 8 小时
#
# **这是剧本**：模型把“昨天”正确换算成世界时窗口，并把回答的时间加回 8 小时。
# 剧本当然不会错；真实模型会不会错，才是有意思的地方。

# %%
TOOLS_A = TOOLS_ALL
model = llm.agent_model(
    call("get_beijing_time"),
    call("geocode_place", "c2", place="广州天河区"),
    call("get_station_history", "c3", lon=113.361, lat=23.125,
         start_time="2026-08-09 16:00:00", end_time="2026-08-10 15:00:00"),
    "昨天下午 15～17 时有雷阵雨，累计 19.9 毫米。",
)
agent = create_agent(model=model, tools=TOOLS_A, system_prompt=wa.SYSTEM_W5_PROMPT)
ra = agent.invoke({"messages": [{"role": "user", "content": "广州天河区昨天的天气如何？"}]})
print(wa.check_calls(tool_calls(ra), EXPECT["yesterday"], hist_tool="get_station_history",
                     fore_tool="get_forecast") or "方案 A：窗口正确")

# %% [markdown]
# ## W5 换算错误的剧本：忘了减 8 小时
#
# **这是剧本**：模型把北京时的“昨天 00～23 时”原样当世界时传进去。窗口错了一段，
# 结果“看起来差不多”，最危险。剧本里模型还直接把世界时当北京时说给用户听。

# %%
model = llm.agent_model(
    call("get_beijing_time"),
    call("geocode_place", "c2", place="广州天河区"),
    call("get_station_history", "c3", lon=113.361, lat=23.125,
         start_time="2026-08-10 00:00:00", end_time="2026-08-10 23:00:00"),
    "昨天 07～09 时有雷阵雨，累计 19.9 毫米。",
)
agent = create_agent(model=model, tools=TOOLS_A, system_prompt=wa.SYSTEM_W5_PROMPT)
rw = agent.invoke({"messages": [{"role": "user", "content": "广州天河区昨天的天气如何？"}]})
show(rw)
print(wa.check_calls(tool_calls(rw), EXPECT["yesterday"], hist_tool="get_station_history",
                     fore_tool="get_forecast"))
print("上面报的窗口错误，就是“忘了减 8 小时”的后果；回答里的 07～09 时也是世界时，不是北京时。")

# %% [markdown]
# ## W5 方案 B：工具直接收北京时（理想行为）
#
# **这是剧本**：模型只负责把“今天”变成北京时 00～23 时，换算交给程序。
# 真实模型下的对比请回 `03_北京时与世界时_W5.ipynb` 第 4 节。

# %%
TOOLS_B = [get_beijing_time, wa.geocode_place, wa.get_station_history_bj, wa.get_forecast_bj]
two = AIMessage(content="", tool_calls=[
    {"name": "get_station_history_bj", "id": "c3",
     "args": {"lon": 113.361, "lat": 23.125, "start_time": "2026-08-11 00:00:00", "end_time": "2026-08-11 08:00:00"}},
    {"name": "get_forecast_bj", "id": "c4",
     "args": {"lon": 113.361, "lat": 23.125, "start_time": "2026-08-11 09:00:00", "end_time": "2026-08-11 23:00:00"}},
])
model = llm.agent_model(
    call("get_beijing_time"),
    call("geocode_place", "c2", place="广州天河区"),
    two,
    "【截至目前的实况】凌晨到早上 8 时没有降水，气温 24～28℃。\n【接下来的预报】17～18 时有阵雨，约 8.5 毫米，请带伞。",
)
agent = create_agent(model=model, tools=TOOLS_B, system_prompt=wa.SYSTEM_W5_TOOL)
rb = agent.invoke({"messages": [{"role": "user", "content": "广州天河区今天的天气如何？"}]})
show(rb)
print(wa.check_calls(tool_calls(rb), EXPECT["today"], hist_tool="get_station_history_bj",
                     fore_tool="get_forecast_bj", bj_args=True) or "方案 B：窗口正确")

# %% [markdown]
# ## 小结
#
# 剧本册只能证明“流程能走通”：工具被执行了、结果回到模型了、回答打印出来了。
# **不能**证明模型自己会选对工具、会算对时区——那要靠 `01` / `02` / `03` 三个正式 notebook 用真实模型跑，再用 `check_calls` 数通过率。
