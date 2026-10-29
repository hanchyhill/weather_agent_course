# %% [markdown]
# # L5-2 台风查询：北京时、核实时区、回查（台风专线 T2～T4）
#
# <!-- course-meta: real-llm -->
#
# - T2：给工具加 `timezone` 参数，换算交给程序。
# - T3：文档和代码对接口时区说法不同，学会用已知个例验证。
# - T4：目标时次没有资料就往回查，查满 24 小时仍没有才算“没有台风”。
#
# 最后一节要问智能体，需要用**真实模型**，`.env` 里的 `MAIN_API_KEY` 必须填好。
# 暂时没有 Key，就先看同目录的 `99_假模型剧本.ipynb`：那里用预设剧本演示同样的流程。

# %%
# 改了 common/、weather_tools/ 里的代码后自动重新加载，不用重启内核
# %load_ext autoreload
# %autoreload 2

import json

from langchain.agents import create_agent

from common import llm
from common.trace import show, tool_calls
from weather_tools import typhoon
from weather_tools.agent_tools import get_beijing_time, get_typhoon_data_by_datetime

# %% [markdown]
# ## T2 北京时查询
#
# huishang_demo 开发者在 `提示词.md` 第 250 行写下的动机：
#
# > 用户总是以北京时进行询问，智能体在调用 tools 时需要反复进行时区转换很容易弄错。不如直接添加一个时区选项。
#
# 先写测试用例，再实现。下面是参考实现的行为：

# %%
cases = [("2026-08-11 08:00:00", "UTC+8"), ("2026-08-11 00:00:00", "UTC")]
for value, tz in cases:
    r = typhoon.query_typhoon(value, tz)
    print(value, tz, "→ tsid", r["tsid"])

try:
    typhoon.query_typhoon("2026-08-11 08:00", "UTC+8")
except ValueError as e:
    print("格式错误被拦下：", e)

# %% [markdown]
# **注意默认值不统一**（已查源码）：huishang_demo 中台风类 8 个工具默认 `UTC+8`，
# ECMWF / 集合预报 / 多模式对比类 12 个工具默认 `UTC`。智能体同时用两类工具时，提示词里要写清各自的默认时区。

# %% [markdown]
# ## T3 核实接口真实时区
#
# - `huishang_demo/台风图像.md` 写：getyphdata “日期为世界时”。
# - 2026-07-24 的提交把参数从 `datetime_utc` 改名为 `datetime_bj`，docstring 写“接口直接使用北京时间”。
#
# 怎么验证？用一个已知个例：资料时次为北京时 02/05/08/11/14/17/20/23，对应世界时 18/21/00/03/06/09/12/15。
# 真实日志里，北京时 08 时的查询，代码改版前发出的请求是 `datetime=...00:00:00`，改版后是 `...08:00:00`，两者返回的 `datetime` 字段都是该时次附近的北京时。
#
# **讲师须在内网实测**后给出本步骤的标准答案（课程设计者没有真实接口）。离线数据按“接口用北京时”制作。
#
# 练习：写出一个测试，在“接口用世界时”和“接口用北京时”两种理解下，会给出不同结果。

# %%
bj_view = typhoon.request_getyphdata("2026-08-11 08:00:00")
utc_view = typhoon.request_getyphdata("2026-08-11 00:00:00")
print("把 08:00 当北京时请求 → tsid", bj_view["tsid"])
print("把 08:00 换成 00:00 请求 → tsid", utc_view["tsid"], "（离线库按北京时制作，所以查不到）")

# %% [markdown]
# ## T4 自动检测过去 24 小时的台风
#
# 规则（`get_typhoon_data_by_datetime`）：从请求时次开始，空就往前推 3 小时，最多推到 24 小时前（9 次）。

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
# 2026-07-29 那条是真实个例：huishang_demo 当天 08 时运行，回查了 21 小时才查到台风红霞。

# %% [markdown]
# ## 接到智能体上：无台风时要如实回答
#
# 目标：问“现在有台风吗”，过去 24 小时都没有时，智能体回答“没有”，**不再去查路径图**。

# %%
SYSTEM = """你是广东省气象台的台风值班助手。
- 用户说的时间都是北京时。查询台风时直接传北京时，不要自己加减 8 小时。
- 台风查询返回 status 为 not_applicable 时，如实回答“过去 24 小时没有活动台风”，不要再调用其他台风工具。"""

model = llm.main_llm()
agent = create_agent(model=model, tools=[get_beijing_time, get_typhoon_data_by_datetime], system_prompt=SYSTEM)
r = agent.invoke({"messages": [{"role": "user", "content": "2026 年 7 月 23 日早上 8 点有台风吗？"}]})
show(r, max_tool_chars=300)
print([c["name"] for c in tool_calls(r)])

# %% [markdown]
# ## 练习
#
# 1. 打开 `练习_台风回查.py` 和 `test_练习_台风回查.py`。先补全测试里的 TODO，再让 Claude Code 实现两个函数。
#    运行：`uv run pytest "lessons/L05_时间与时区/test_练习_台风回查.py" --run-exercises`
# 2. 真实模型下问“2026 年 7 月 29 日早上 8 点有台风吗”，看智能体能不能报出红霞，并说明资料是 21 小时前的。
# 3. 讨论：回查窗口为什么是 24 小时、步长为什么是 3 小时？你会选多长？
