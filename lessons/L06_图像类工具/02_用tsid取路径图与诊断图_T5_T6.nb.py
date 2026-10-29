# %% [markdown]
# # L6-2 用 tsid 串联：路径图与诊断图（台风专线 T5、T6）
#
# <!-- course-meta: real-llm -->
#
# - T5：台风查询结果里有 `tsid`，拿它去取路径预报图，交给视觉模型判读。
# - T6：诊断图服务用另一套编号，业务编号直接用会取不到图。
#
# 个例：2024 年第 11 号台风摩羯（tsid=736）。路径图来自 mllm_test（广州 BCGZ 路径图，文件名按世界时）。
#
# T5-3 要问智能体，需要用**真实模型**，`.env` 里的 `MAIN_API_KEY`、`VLM_API_KEY` 必须填好。
# 暂时没有 Key，就先看同目录的 `99_假模型剧本.ipynb`：那里用预设剧本演示同样的流程。

# %%
# 改了 common/、weather_tools/ 里的代码后自动重新加载，不用重启内核
# %load_ext autoreload
# %autoreload 2

from IPython.display import Image, display
from langchain.agents import create_agent

from common import llm
from common.trace import show, tool_calls
from weather_tools import typhoon
from weather_tools.agent_tools import (
    get_typhoon_data_by_datetime,
    interpret_tc_track_forecast_chart,
    resolve_diagnostic_tsid,
)

# %% [markdown]
# ## T5-1 先查台风，拿到 tsid

# %%
r = typhoon.query_typhoon_with_lookback("2024-09-03 08:00:00")
print(typhoon.summarize(r))
tsid = str(r["tsid"][0])

# %% [markdown]
# ## T5-2 路径图的时次规则
#
# - 预报时间用北京时，小时必须是 02/08/14/20（对应世界时 18/00/06/12）。
# - 请求时次没有图时，先试最近的下一个时次，再试上一个时次，最多 3 个。用了替代时次要说明，不能悄悄换。
#
# 离线数据故意缺了北京时 9 月 4 日 02 时的图，看看回退：

# %%
for t in ["2024-09-03 08:00:00", "2024-09-04 02:00:00"]:
    path, used, fb = typhoon.track_image_path(tsid, t)
    print(t, "候选", typhoon.track_candidates(t), "→ 实际用", used, "（回退）" if fb else "")

path, used, _ = typhoon.track_image_path(tsid, "2024-09-03 08:00:00")
display(Image(filename=str(path), width=700))

# %% [markdown]
# ## T5-3 交给智能体：tsid 必须来自查询结果
#
# 检查点：智能体传给路径图工具的 tsid，必须和台风查询返回的一致，不能自己编。

# %%
SYSTEM = """你是广东省气象台的台风值班助手。用户说的时间都是北京时。
取路径图前，必须先调用 get_typhoon_data_by_datetime 拿到 tsid。
返回多个台风时，每个台风都要给出结论。"""

model = llm.main_llm()
agent = create_agent(model=model, system_prompt=SYSTEM,
                     tools=[get_typhoon_data_by_datetime, interpret_tc_track_forecast_chart])
res = agent.invoke({"messages": [{"role": "user", "content": "2024 年 9 月 3 日 08 时的台风路径怎么走？"}]})
show(res, max_tool_chars=300)

# %%
calls = tool_calls(res)
queried = [c for c in calls if c["name"] == "get_typhoon_data_by_datetime"]
track = [c for c in calls if c["name"] == "interpret_tc_track_forecast_chart"]
print("先查台风再取路径图：", bool(queried) and calls.index(queried[0]) < calls.index(track[0]))
print("tsid 来自查询结果：", all(c["args"]["tsid"] == tsid for c in track))

# %% [markdown]
# ## T5-4 多个台风同时活动
#
# 2026-08-11 08 时有白海豚、灿鸿两个台风。常见错误：只分析第一个。
# （离线数据没有这两个台风的路径图，这里只看查询结果和提示词约束。）

# %%
print(typhoon.summarize(typhoon.query_typhoon_with_lookback("2026-08-11 08:00:00")))

# %% [markdown]
# ## T6 诊断图：两套编号
#
# 诊断图（引导气流、风切变、海温、涡度、散度）服务用的台风编号和台风动态接口不是同一套。
# 真实系统要先请求编号转换接口，用返回的 `data.TSID`。文档示例：业务编号 554 对应诊断图编号 803。
#
# 练习：先不告诉 AI 有两套编号，直接让它用 tsid 拼诊断图地址，看能否发现问题。

# %%
for t in ["554", "736"]:
    print(t, "→", resolve_diagnostic_tsid.invoke({"business_tsid": t}))

# %% [markdown]
# 诊断图文件名规则（`huishang_demo/src/tools/url_config.py`），注意不同要素分隔符不一样：
#
# | 要素 | 文件名 |
# |---|---|
# | wgt700-850、wgt500-850、vor850、div200 | `{诊断图编号}{要素}-{YYYYMMDDHH}.png` |
# | BCGZsteerflow、ws4x4、ws7x7、sst、sstmax | `{诊断图编号}{要素}{YYYYMMDDHH}.png` |
#
# 起报时次：北京时 08/20（世界时 00/12），文件名用世界时。


# %%
def diagnostic_filename(diag_tsid: str, element: str, init_time_utc: str) -> str:
    dash = element in ("wgt700-850", "wgt500-850", "vor850", "div200")
    return f"{diag_tsid}{element}{'-' if dash else ''}{init_time_utc}.png"


print(diagnostic_filename("803", "ws4x4", "2025090712"))
print(diagnostic_filename("803", "wgt700-850", "2025090712"))
